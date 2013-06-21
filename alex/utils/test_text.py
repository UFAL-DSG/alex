#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == "__main__":
    import autopath

import unittest

import alex.utils.text

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

if __name__ == '__main__':
    unittest.main()
