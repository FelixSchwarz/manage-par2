#!/usr/bin/env python3
"""
manage-par2.

Usage:
  manage-par2 create [options] <SOURCEDIR> <RECOVERYDIR>

Options:
    --fast      do not run as "background" process [default: False]
"""
import os
import subprocess
import sys

from docopt import docopt


def find_missing_files(source_dir, recovery_dir):
    abs_source_dir = os.path.abspath(source_dir)
    get_relative_dir = lambda path: path[len(abs_source_dir)+1:]

    for root_dir, dirnames, filenames in os.walk(abs_source_dir):
        relative_dir = get_relative_dir(root_dir)
        for filename in filenames:
            source_path = os.path.join(root_dir, filename)
            recovery_file_path = os.path.join(recovery_dir, relative_dir, filename) + '.par2'
            # possible optimization: do a scandir on recovery_dir_path and match manually using sets
            # however this is not important for "create" as most of the time is
            # spent on calculating the parity data anyway.
            if not os.path.exists(recovery_file_path):
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


if __name__ == '__main__':
    arguments = docopt(__doc__)

    source_dir = arguments['<SOURCEDIR>']
    recovery_dir = arguments['<RECOVERYDIR>']
    work_in_background = not arguments['--fast']

    if work_in_background:
        pid = os.getpid()
        subprocess.check_call(('renice', '19', str(pid)), stdout=subprocess.PIPE)
        subprocess.check_call(('ionice', '--class', 'idle', '-p', str(pid)))

    missing_files = find_missing_files(source_dir, recovery_dir)
    for i, missing_data in enumerate(missing_files):
        create_par2_data(missing_data, source_dir)
        sys.stdout.write('.')
        sys.stdout.flush()

