#!/usr/bin/env python
# vim: set fileencoding=utf-8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
Unit tests for alex.corpustools.get_jasr_confnets.

"""

from __future__ import unicode_literals

if __name__ == "__main__":
    import autopath

import codecs
import os
import os.path
import re
import unittest

from alex.utils.config import Config

import get_jasr_confnets

_script_dir = os.path.dirname(os.path.abspath(__file__))
_default_cfg_fname = os.path.join(_script_dir, '..', 'resources',
                                  'default.cfg')


class TestJuliusConfnetDecoding(unittest.TestCase):
    data_fname = os.path.join(_script_dir, '.test_data')

    def setUp(self):
        cfg = Config(_default_cfg_fname)
        cfg.config['ASR']['Julius']['msg_timeout'] = 10.
        cfg.config['ASR']['Julius']['timeout'] = 10.
        cfg.config['corpustools']['get_jasr_confnets']['rt_ratio'] = 0.
        self.cfg = cfg

    def test_basic(self):
        # Run the code.
        self.out_fname = os.path.join(self.data_fname, 'jul.out')
        get_jasr_confnets.main(self.data_fname, self.out_fname, self.cfg)
        # Check its output.
        expected_out = ['^a.wav => (?!u([\'"])None\\1)',
                        '^b.wav => u([\'"])None\\1']
        with codecs.open(self.out_fname, 'r', encoding='UTF-8') as outfile:
            sorted_lines = sorted(outfile)
        self.assertEqual(len(sorted_lines), 2)
        for expected_re, line in zip(expected_out, sorted_lines):
            self.assertTrue(re.search(expected_re, line))
        # Check that Julius is not running anymore.
        print
        print "Checking that Julius is dead..."
        self.assertTrue(os.system('ps -C julius'))
        print "Yes, it is."

    def tearDown(self):
        os.unlink(self.out_fname)


if __name__ == '__main__':
    unittest.main()
