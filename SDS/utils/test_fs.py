#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set fdm=marker :
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
Unit tests for SDS.util.fs.

"""

import os
import os.path
import tempfile
import unittest
from fs import normalise_path, find


class TestFind(unittest.TestCase):

    def setUp(self):
    #{{{
        """
        Creates a playground of a directory tree.
        It looks like this:
        <testroot>/
          - a/
              - aa/
              - ab/
              - ac/
                  - aca/
                      - acaa/
                      - acab -> baaaa
          - b/
              - ba/
                  - baa/
                      - baaa/
                          - baaaa -> daaa
                          - baaab/
                              - baaaba/
                                  - baaabaa/
                                  - baaabab -> ca
          - c/
              - ca/
                  - caa/
                  - cab/
                      - caba/
                  - cac -> db
          - d/
              - da/
                  - daa/
                      - daaa -> acab
              - db -> baaaba

        """
        self.testroot = tempfile.mkdtemp()
        # Make the directory structure.
        # list of all the dirs {{{
        dirs = [
            (self.testroot, 'a',),
            (self.testroot, 'a', 'aa'),
            (self.testroot, 'a', 'ab'),
            (self.testroot, 'a', 'ac'),
            (self.testroot, 'a', 'ac', 'aca'),
            (self.testroot, 'a', 'ac', 'aca', 'acaa'),
            (self.testroot, 'b',),
            (self.testroot, 'b', 'ba'),
            (self.testroot, 'b', 'ba', 'baa'),
            (self.testroot, 'b', 'ba', 'baa', 'baaa'),
            (self.testroot, 'b', 'ba', 'baa', 'baaa', 'baaab'),
            (self.testroot, 'b', 'ba', 'baa', 'baaa', 'baaab', 'baaaba'),
            (self.testroot, 'b', 'ba', 'baa', 'baaa', 'baaab', 'baaaba',
                'baaabaa'),
            (self.testroot, 'c',),
            (self.testroot, 'c', 'ca'),
            (self.testroot, 'c', 'ca', 'caa'),
            (self.testroot, 'c', 'ca', 'cab'),
            (self.testroot, 'c', 'ca', 'cab', 'caba'),
            (self.testroot, 'd',),
            (self.testroot, 'd', 'da'),
            (self.testroot, 'd', 'da', 'daa')
        ]
        # }}}
        for dir_ in dirs:
            os.mkdir(os.path.join(*dir_))
        # Make the symlinks.
        #{{{
        symlinks = [
            (self._pathto('acab'), self._pathto('baaaa')),
            (self._pathto('baaaa'), self._pathto('daaa')),
            (self._pathto('baaabab'), self._pathto('ca')),
            (self._pathto('cac'), self._pathto('db')),
            (self._pathto('daaa'), self._pathto('acab')),
            (self._pathto('db'), self._pathto('baaaba'))
        ]
        for symlink in symlinks:
            os.symlink(symlink[1], symlink[0])
        #}}}
    #}}}

    def tearDown(self):
    #{{{
        """Deletes the mock-up directory tree."""
        for root, dirs, files in os.walk(self.testroot, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    os.unlink(path)
                else:
                    os.rmdir(path)
    #}}}

    def test_depth(self):
        """Tests mindepth and maxdepth."""
    #{{{
        self.assertEqual(
            find(self.testroot, '*', 0, 1), self._format_result(
                '.', 'a', 'b', 'c', 'd'))
        self.assertEqual(
            find(self._pathto('ac'), '*', 0, 1), self._format_result(
                'ac', 'aca'))
        self.assertEqual(
            find(self._pathto('ac'), '*', 0, 0), self._format_result(
                'ac',))
        self.assertEqual(
            find(self._pathto('ac'), '*', 0, -1), set())
    #}}}

    def test_symlinks1(self):
        """Basic test for symlinks."""
    #{{{
        self.assertEqual(
            find(self._pathto('ac'), '*', 0, 2), self._format_result(
                'ac','aca','acaa','acab'))
        self.assertEqual(
            find(self._pathto('baaab'), '*', 2, 4), self._format_result(
                'baaabaa', 'ca',
                'caa', 'cab', 'cac',
                'caba'))
    #}}}


    def test_wrong_args(self):
        """Test for handling wrong arguments."""
    #{{{
        self.assertEqual(
            find(self._pathto('baaaba'), '*', 41, 35), set())
    #}}}

    def test_globs(self):
        """Tests processing of the selection glob."""
    #{{{
        self.assertEqual(
            find(self._pathto('ac'), '*b', 0, 2), self._format_result(
                'acab'))
        self.assertEqual(
            find(self._pathto('ac'), 'aca?', 0, 2), self._format_result(
                'acaa', 'acab'))
        self.assertEqual(
            find(self._pathto('b'), '[!b]*', 4, 7), self._format_result(
                'ca', 'caa', 'cab'))
        self.assertEqual(
            find(self._pathto('b'), '??[bc]', 4, 7), self._format_result(
                'cab'))
    #}}}

    def test_cycles(self):
        """Test the processing of cycles in the directory structure."""
        self.assertEqual(
            find(self._pathto('b'), 'ca??', 0, None), self._format_result(
                'caba'))
        self.assertEqual(
            find(self._pathto('b'), 'c?', 0, None), self._format_result(
                'ca'))

    def test_ignore_globs(self):
        """Test the functionality of ignore globs."""
        self.assertEqual(
            find(self._pathto('ac'), '*', 0, 2, ['aca?']),
            self._format_result('ac','aca'))
        self.assertEqual(
            find(self._pathto('ac'), '*', 0, 2, ['ac','ac?a']),
            set())
        self.assertEqual(
            find(self._pathto('baaab'), '*', 2, 4, ['*b']),
            self._format_result('baaabaa', 'ca', 'caa', 'cac'))

    # TODO Test other arguments of the function.

    def _pathto(self, fname):
        """
        Returns the absolute path to one of the created test directories (or
        links). The root can be specified by the name '.'.
        """
        #{{{
        if fname == '.':
            return self.testroot
        dirs = [self.testroot] +\
               [fname[:preflen] \
                  for preflen in xrange(1, len(fname) + 1)]
        return os.path.join(*dirs)
        #}}}

    def _format_result(self, *fnames):
        return set(map(
            lambda fname: normalise_path(self._pathto(fname)),
            fnames))

if __name__ == '__main__':
    unittest.main()
