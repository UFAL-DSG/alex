#!/usr/bin/env python
# vim: set fileencoding=utf-8
#
# 2013-06
# Matěj Korvas
"""
This module is meant to collect functionality for handling call logs -- both
working with the call log files in the filesystem, and parsing them.
"""

import copy
import glob
import os
import os.path

if __name__ == "__main__":
    import autopath

from alex.utils.fs import find


def _build_find_kwargs(user_kwargs, **kwargs):
    """
    Builds arguments for the `find' function, ensuring they are consistent.
    """
    find_kwargs = copy.copy(user_kwargs)
    # Remove any positional arguments specified by name.
    if 'dir_' in find_kwargs:
        del find_kwargs['dir_']
    if 'glob_' in find_kwargs:
        del find_kwargs['glob_']
    # Override user kwargs by ours.
    find_kwargs.update(kwargs)
    return find_kwargs


def find_with_ignorelist(infname, pat, ignore_list_file=None, find_kwargs=dict()):
    """
    Finds specific files below the paths specified and returns their filenames.

    Arguments:
        pat -- globbing pattern specifying the files to look for
        infname -- either a directory, or a file.  In the first case, wavs are
            looked for below that directory.  In the latter case, the file is
            read line by line, each line specifying a directory or a glob
            determining the wav to include.
        ignore_list_file -- a file of absolute paths or globs (can be mixed)
            specifying wavs that should be excluded from the results
        find_kwargs -- if provided, this dictionary is used as additional
            keyword arguments for the function `utils.fs.find' for finding
            positive examples of files (not the ignored ones)

    Returns a set of paths to files satisfying the criteria.

    """

    # Read in the ignore list.
    ignore_paths = set()
    ignore_globs = set()
    if ignore_list_file:
        for path_or_glob in ignore_list_file:
            path_or_glob = path_or_glob.rstrip('\n')
            # For lines that list absolute paths,
            if os.path.abspath(path_or_glob) == os.path.normpath(path_or_glob):
                # add them to the list of paths to ignore.
                ignore_paths.add(path_or_glob)
            # For other lines, treat them as basename globs.
            else:
                ignore_globs.add(path_or_glob)
        ignore_list_file.close()

    # Get all files matching `pat', skipping ignore globs and ignore paths.
    #
    # First option: the infile is actually a directory.  Then, take all
    # matching files from below that directory.
    if os.path.isdir(infname):
        find_kwargs = _build_find_kwargs(find_kwargs,
                                         ignore_globs=ignore_globs,
                                         ignore_paths=ignore_paths)
        if 'mindepth' not in find_kwargs:
            find_kwargs['mindepth'] = 1
        file_paths = set(find(infname, pat, **find_kwargs))
    # Second option: the infile is a file listing all paths to check for
    # matching files.
    else:
        file_paths = set()
        find_kwargs = _build_find_kwargs(find_kwargs, mindepth=1, maxdepth=1,
                                         ignore_globs=ignore_globs,
                                         ignore_paths=ignore_paths)
        with open(infname, 'r') as inlist:
            for line in inlist:
                line = line.rstrip('\n')
                # If the line contains directories:
                if os.path.isdir(line):
                    file_paths.update(find(line, pat, **find_kwargs))
                # If it is not a directory name, treat the line as a file glob.
                else:
                    new_paths = [os.path.abspath(f) for f in glob.glob(line)]
                    file_paths.update(new_paths)

    # Find all files in ignore paths and remove them from the returned files,
    # to be sure that symlinks from other, not ignored paths did not add them.
    for ignore_path in ignore_paths:
        file_paths.difference_update(
            find(ignore_path, pat, mindepth=1, maxdepth=1))
    for ignore_glob in ignore_globs:
        file_paths.difference_update(
            os.path.abspath(fname) for fname in glob.glob(ignore_glob))

    return file_paths


def find_wavs(infname, ignore_list_file=None):
    """
    Finds wavs below the paths specified and returns their filenames.

    Arguments:
        infname -- either a directory, or a file.  In the first case, wavs are
            looked for below that directory.  In the latter case, the file is
            read line by line, each line specifying a directory or a glob
            determining the wav to include.
        ignore_list_file -- a file of absolute paths or globs (can be mixed)
            specifying wavs that should be excluded from the results

    Returns a set of paths to files satisfying the criteria.

    """
    return find_with_ignorelist(infname, '*.wav', ignore_list_file)


_log_fnames = ('user-transcription.norm.xml',
               'user-transcription.xml',
               'user-transcription-all.xml')

def _log_fname_key(xml_path_tup):
    try:
        return _log_fnames.index(xml_path_tup[1])
    except:
        return 42  # must be a number greater than len(_log_fnames)


def find_logs(infname, ignore_list_file=None, verbose=False):
    """
    Finds CUED logs below the paths specified and returns their filenames.
    The logs are determined as files matching one of the following patterns:

        user-transcription.norm.xml
        user-transcription.xml
        user-transcription-all.xml

    If multiple patterns are matched by files in the same directory, only the
    first match is taken.

    Arguments:
        infname -- either a directory, or a file.  In the first case, logs are
            looked for below that directory.  In the latter case, the file is
            read line by line, each line specifying a directory or a glob
            determining the log to include.
        ignore_list_file -- a file of absolute paths or globs (can be mixed)
            specifying logs that should be excluded from the results
        verbose -- print lots of output?

    Returns a set of paths to files satisfying the criteria.

    """
    xml_paths = find_with_ignorelist(infname, '*.xml', ignore_list_file)
    if verbose:
        print "XML files found:"
        for xml_path in xml_paths:
            print "    {path}".format(path=xml_path)
    xml_path_tups = map(os.path.split, xml_paths)
    # sort | uniq the paths, taking uniq over their prefixes (call log dirs)
    # only.
    # XXX Here we rely on dict() updating the value for a key when a new value
    # for the key comes later in the sequence.
    dir2base = dict(sorted(xml_path_tups, key=_log_fname_key, reverse=True))
    return map(os.sep.join, dir2base.iteritems())
