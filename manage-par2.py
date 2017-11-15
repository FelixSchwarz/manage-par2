#!/usr/bin/env python3
"""
manage-par2.

Usage:
  manage-par2 create [options] <SOURCEDIR> <RECOVERYDIR>
  manage-par2 list-outdated <SOURCEDIR> <RECOVERYDIR>
  manage-par2 delete-outdated <SOURCEDIR> <RECOVERYDIR>
  manage-par2 verify <SOURCEDIR> <RECOVERYDIR>

Options:
    --fast      do not run as "background" process [default: False]
"""
import os
import re
import subprocess
import sys

from docopt import docopt


def find_missing_files(source_dir, recovery_dir):
    get_relative_dir = lambda path: path[len(source_dir)+1:]

    for root_dir, dirnames, filenames in os.walk(source_dir):
        relative_dir = get_relative_dir(root_dir)
        for filename in filenames:
            source_path = os.path.join(root_dir, filename)
            recovery_file_path = os.path.join(recovery_dir, relative_dir, filename) + '.par2'
            # possible optimization: do a scandir on recovery_dir_path and match manually using sets
            # however this is not important for "create" as most of the time is
            # spent on calculating the parity data anyway.
            if not os.path.exists(recovery_file_path):
                yield (source_path, recovery_file_path)

def find_existing_files(source_dir, recovery_dir):
    get_relative_dir = lambda path: path[len(source_dir)+1:]
    for root_dir, dirnames, filenames in os.walk(source_dir):
        relative_dir = get_relative_dir(root_dir)
        for filename in filenames:
            source_path = os.path.join(root_dir, filename)
            recovery_file_path = os.path.join(recovery_dir, relative_dir, filename) + '.par2'
            if os.path.exists(recovery_file_path):
                yield (source_path, recovery_file_path)


def create_par2_data(missing_data, source_base_dir, *, redundancy_percentage=10):
    source_path, recovery_file_path = missing_data
    cmd = (
        'par2', 'create',
        '-qq',
        '-r%d' % redundancy_percentage,
        '-B'+source_base_dir,
        recovery_file_path, source_path
    )
    subprocess.check_call(cmd, shell=False, stdout=subprocess.PIPE)


def verify_par2_data(existing_data, source_base_dir):
    source_path, recovery_file_path = existing_data
    cmd = (
        'par2', 'verify',
        #'-qq',
        '-B'+source_base_dir,
        recovery_file_path, source_path
    )
    verify_process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)
    (stdout_data, stderr_data) = verify_process.communicate()
    exit_code = verify_process.returncode
    if exit_code == 0:
        return
    sys.stderr.write('BAD %s\n' % source_path)
    sys.stderr.write('   use "par2 repair -B%s %s"\n' % (source_base_dir, recovery_file_path))


def find_outdated_files(source_dir, recovery_dir):
    get_relative_dir = lambda path: path[len(source_dir)+1:]

    for root_dir, dirnames, filenames in os.walk(source_dir):
        relative_dir = get_relative_dir(root_dir)
        recovery_dir_path = os.path.join(recovery_dir, relative_dir)
        for filename in filenames:
            source_path = os.path.join(root_dir, filename)
            recovery_file_path = os.path.join(recovery_dir_path, filename) + '.par2'
            if not os.path.exists(recovery_file_path):
                continue
            parity_stat = os.stat(recovery_file_path)
            if parity_stat.st_size == 0:
                yield (source_path, recovery_file_path)
            else:
                source_stat = os.stat(source_path)
                if (source_stat.st_mtime > parity_stat.st_mtime):
                    yield (source_path, recovery_file_path)


def find_deleted_files(source_dir, recovery_dir):
    get_relative_dir = lambda path: path[len(recovery_dir)+1:]
    volname_regex = re.compile('.+\.vol\d+\+\d+\.par2$')

    for root_dir, dirnames, filenames in os.walk(recovery_dir):
        relative_dir = get_relative_dir(root_dir)
        source_dir_path = os.path.join(source_dir, relative_dir)
        for filename in filenames:
            if volname_regex.search(filename):
                continue
            elif not filename.endswith('.par2'):
                continue
            source_filename = filename[:-5]
            source_path = os.path.join(source_dir_path, source_filename)
            if not os.path.exists(source_path):
                recovery_file_path = os.path.join(root_dir, filename)
                yield (source_path, recovery_file_path)


def delete_par2_files(outdated_files):
    for par2_path in tuple(outdated_files):
        par2_dir = os.path.dirname(par2_path)
        par2_filename = os.path.basename(par2_path)
        volname_regex = re.compile('^%s\.vol\d+\+\d+\.par2$' % par2_filename[:-5])
        for filename in os.listdir(par2_dir):
            if not volname_regex.search(filename):
                continue
            par2_vol_path = os.path.join(par2_dir, filename)
            os.unlink(par2_vol_path)
        os.unlink(par2_path)


if __name__ == '__main__':
    arguments = docopt(__doc__)

    source_dir_str = arguments['<SOURCEDIR>']
    recovery_dir = arguments['<RECOVERYDIR>']
    work_in_background = not arguments['--fast']
    list_outdated = arguments['list-outdated']
    delete_outdated = arguments['delete-outdated']
    verify = arguments['verify']

    if work_in_background:
        pid = os.getpid()
        subprocess.check_call(('renice', '19', str(pid)), stdout=subprocess.PIPE)
        subprocess.check_call(('ionice', '--class', 'idle', '-p', str(pid)))

    source_dir = os.path.abspath(source_dir_str)

    if not os.path.exists(source_dir):
        sys.stderr.write('data directory "%s" does not exist.\n' % source_dir_str)
        sys.exit(51)

    if arguments['create']:
        missing_files = find_missing_files(source_dir, recovery_dir)
        for i, missing_data in enumerate(missing_files):
            create_par2_data(missing_data, source_dir)
            sys.stdout.write('.')
            sys.stdout.flush()
    elif verify:
        existing_files = tuple(find_existing_files(source_dir, recovery_dir))
        for existing_data in existing_files:
            verify_par2_data(existing_data, source_dir)
            sys.stdout.write('.')
            sys.stdout.flush()
        if len(existing_files) > 0:
            sys.stdout.write('\n')
    else:
        outdated_files = set()
        for outdated_data in find_outdated_files(source_dir, recovery_dir):
            outdated_files.add(outdated_data[1])
        for deleted_data in find_deleted_files(source_dir, recovery_dir):
            outdated_files.add(deleted_data[1])
        if list_outdated:
            for outdated_path in outdated_files:
                print(outdated_path)
        elif delete_outdated:
            delete_par2_files(outdated_files)

