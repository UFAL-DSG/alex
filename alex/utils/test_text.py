#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == "__main__":
    import autopath

import unittest
import alex.utils.text
from alex.utils.text import WordDistance


class TestString(unittest.TestCase):
    def test_split_by(self):
        # make sure the alex.utils.text.split_by splits the string correctly

        r = alex.utils.text.split_by(
            'inform(name="Taj Mahal")&request(phone)', '&', '(', ')', '"')
        self.assertEqual(r, ['inform(name="Taj Mahal")', 'request(phone)'])

        r = alex.utils.text.split_by('"&"', '&', '(', ')', '"')
        self.assertEqual(r, ['"&"', ])

        r = alex.utils.text.split_by('(&)', '&', '(', ')', '"')
        self.assertEqual(r, ['(&)', ])

        # should raise an exception for unclosed parentheses
        self.assertRaises(ValueError, alex.utils.text.split_by, *[
                          '((()))))', ',', '(', ')', ""])

    def test_parse_command(self):
        # make sure the alex.utils.text.parse_command splits the command correctly
        r = alex.utils.text.parse_command('call(destination="1245",opt="X")')
        self.assertEqual(r, {"__name__": "call", "destination": "1245", "opt": "X"})


class TestWordDistance(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestWordDistance, self).__init__(*args, **kwargs)
        self.penalties = (1.0, 2.0, 1.0)
        self.dist_data = [
                ([1, 1 ,1],[0, 0, 0], 6),
                ([0, 1,],[0, 0, 0], 3),
                ([1, 0, 0],[0, 0, 0], 2),
                ([0, 1, 0],[0, 0, 0], 2),
                ([0, 0, 1],[0, 0, 0], 2),
                ]
        self.path_data = [
                ([0,0],[0,0],[(None,None),(None,None)]),
                ([1],[],[(1, None)]),
                ([],[1],[(None, 1)]),
                ([1,1],[0,0],[(1,0),(1,0)]),
                ([1],[0],[(1,0)]),
                ]

    def test_distance(self):
        for s, t, d in self.dist_data:
            wd = WordDistance(s, t, self.penalties)
            d_test = wd.compute_dist()
            self.assertEqual(d_test, d)

    def test_path(self):
        for s, t, gold_path in self.path_data:
            wd = WordDistance(s,t, self.penalties)
            path = wd.best_path()
            self.assertEqual(path, gold_path)


if __name__ == '__main__':
    unittest.main()
