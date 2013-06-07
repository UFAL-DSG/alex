#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set fdm=marker :
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
Filesystem utility functions.

"""

import fnmatch
import glob
import os
import os.path
import re


def normalise_path(path):
    """
    Normalises a filesystem path using tilde expansion, absolutising and
    normalising the path, and resolving symlinks.

    """
    return os.path.realpath(os.path.abspath(os.path.expanduser(path)))


def find(dir_, glob_, mindepth=2, maxdepth=6, ignore_globs=list(),
         ignore_paths=None, follow_symlinks=True, prune=False, rx=None,
         notrx=None):
    """\
    A simplified version of the GNU `find' utility.  Lists files with basename
    matching `glob_' found in `dir_' in depth between `mindepth' and
    `maxdepth'.

    The `ignore_globs' argument specifies a glob for basenames of files to be
    ignored.  The `ignore_paths' argument specifies a collection of real
    absolute pathnames that are pruned from the search.  For efficiency
    reasons, it should be a set.

    In the current implementation, the traversal resolves symlinks before the
    file name is checked. However, taking symlinks into account can be
    forbidden altogether by specifying `follow_symlinks=False'. Cycles during
    the traversal are avoided.

        - prune: whether to prune the subtree below a matching directory
        - rx: regexp to use as an additional matching criterion apart from
            `glob_'; the `re.match' function is used, as opposed to `re.find'
        - notrx: like `rx' but this specifies the regexp that must NOT match

    The returned set of files consists of real absolute pathnames of those
    files.

    """
    # Check the arguments.
    if isinstance(mindepth, int) and isinstance(maxdepth, int) and mindepth > maxdepth:
        return set()

    # Normalise paths specified.
    dir_ = normalise_path(dir_)
    if ignore_paths:
        ignore_paths = map(normalise_path, ignore_paths)

    # Special case: mindepth == 0. {{{
    ret = set() # Return an empty set by default.
    if mindepth is None or mindepth == 0:
        dirname = os.path.basename(dir_)
        # Apply the path filter.
        if ignore_paths and dir_ in ignore_paths:
            return set()
        # Apply the glob filter.
        for ignore_glob in ignore_globs:
            if fnmatch.fnmatch(dirname, ignore_glob):
                return set()
        # Match the glob.
        if (fnmatch.fnmatch(dirname, glob_)
                and (rx is None or re.match(rx, dirname))
                and (notrx is None or not re.match(notrx, dirname))):
            ret = set((dir_, ))
        # Special case: also maxdepth == 0. Or we prune the whole subtree.
        if maxdepth == 0 or (ret and prune):
            return ret
    # }}}

    # If ignored paths are specified and non-empty,
    if ignore_paths:
        # Build a function filtering out the specified ignored paths.
        ignore_path_filter = lambda path_data: path_data[1] not in ignore_paths
    else:
        # Build an all-true filter.
        ignore_path_filter = lambda path_data: True

    # Call the implementation with the filter function.
    ret.update(_find_ignorefunc(dir_, glob_, mindepth, maxdepth,
                                ignore_globs, ignore_path_filter,
                                follow_symlinks, prune, rx, notrx, set())[0])

    return ret


def _find_ignorefunc(dir_, glob_, mindepth, maxdepth, ignore_globs=list(),
                     ignore_path_filter=lambda _: True, follow_symlinks=True,
                     prune=False, rx=None, notrx=None, visited=set()):
    """\
    Implements the same functionality as the `find' function in this module.
    The difference is that the ignored paths are specified by a function.
    `ignore_path_filter' is a function that takes a tuple (basename,
    normalised name) and returns False iff the file should be ignored.
    `visited' is the set of normalised names of directories visited before this
    (recursive) call.

    This function cannot handle the depth of 0. That is handled by the wrapper
    function `find'.

    """
    #{{{
    # List files/dirs in this directory, and remove symlinks if asked to.
    if os.path.isdir(dir_):
        children = os.listdir(dir_)
    else:
        children = [dir_]
    if follow_symlinks is False:
        children = filter(lambda path: not os.path.islink(path),
                          children)
    # Resolve symlinks and store both the real path and the basename for each
    # child.
    children = map(
        lambda basename: normalise_path(os.path.join(dir_, basename)),
        children)
    children = map(
        lambda realpath: (os.path.basename(realpath), realpath),
        children)
    # Filter out ignored paths.
    children = filter(ignore_path_filter, children)
    # Apply ignore globs.
    for ignore_glob in ignore_globs:
        children = filter(
            lambda child: not fnmatch.fnmatch(child[0], ignore_glob),
            children)
    # Match children by the glob.
    if mindepth is None or mindepth < 2:
        matched = filter(
            lambda child: (fnmatch.fnmatch(child[0], glob_)
                           and (rx is None or re.match(rx, child[0]))
                           and (notrx is None or not re.match(notrx, child[0]))),
            children)
        matched = set(map(lambda child: child[1], matched))
    else:
        matched = set()
    # Recur to subdirectories.
    if maxdepth is None or maxdepth > 1:
        subdirs = set(map(
            lambda path_data: path_data[1],
            filter(lambda child: os.path.isdir(child[1]), children)))\
            - visited
        if prune:
            subdirs -= matched
        for subdir in subdirs:
            visited.add(dir_)
            more_matched, more_visited = \
                _find_ignorefunc(subdir, glob_,
                                 mindepth - 1 if isinstance(mindepth, int)
                                    else None,
                                 maxdepth - 1 if isinstance(maxdepth, int)
                                    else None,
                                 ignore_globs, ignore_path_filter,
                                 follow_symlinks, prune, rx, notrx, visited)
            matched.update(more_matched)
            visited.update(more_visited)
    # Return.
    return matched, visited
    #}}}
