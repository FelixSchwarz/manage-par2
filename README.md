manage-par2
=============

This is a small wrapper script to manage "par2" parity data. It requires par2 >= 0.7.

    Usage:
      manage-par2 create [options] <SOURCEDIR> [<RECOVERYDIR>]
      manage-par2 list-outdated <SOURCEDIR> [<RECOVERYDIR>]
      manage-par2 delete-outdated <SOURCEDIR> [<RECOVERYDIR>]
      manage-par2 verify <SOURCEDIR> [<RECOVERYDIR>]
    
    Options:
        --fast      do not run as "background" process [default: False]

"manage-par2 create" creates "par2" files for each file in <SOURCEDIR> (recursively).
Parity data is stored in a separate directory (RECOVERYDIR, if not set it creates
a new directory named after SOURCEDIR but with ".parity" suffix).
That means you can repair corrupted files (bitflips) but not files which are deleted.

The reason for this is that I want to protect a somewhat big directory tree (1-2 TB)
where files are added/deleted on a regular basis. In order to guard against file
deletions "par2" needs to reread the complete data set every time which just takes
too long (even with a saturated Gbit connection).

You can run "manage-par2 create" multiple times. It will skip source files which already
have a corresponding par2 file then.

The commands "list-outdated" and "delete-outdated" check for any par2 files which do
not have a corresponding source file or where the source file has an higher mtime than
the par2 file. The latter usually points to an updated source file so the par2 data
should be deleted and recreated. However a source modification might also be
indicative of a corrupted source file which was fixed up by some kind of "fsck"-like
tool.

"manage-par2 verify" verifies the actual par2 data against source files… Well I guess
you already suspected that, right? ;-). It can take quite a while for bigger datasets
as all source data will be read.

Currently there is no special support to repair corrupted files - use "par2"
directly for that.
