#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == "__main__":
    import autopath


import unittest

import SDS.utils.text

class TestString(unittest.TestCase):
    def test_split_by(self):
        # make sure the SDS.utils.text.split_by splits the string correctly

        r = SDS.utils.text.split_by(
            'inform(name="Taj Mahal")&request(phone)', '&', '(', ')', '"')
        self.assertEqual(r, ['inform(name="Taj Mahal")', 'request(phone)'])

        r = SDS.utils.text.split_by('"&"', '&', '(', ')', '"')
        self.assertEqual(r, ['"&"', ])

        r = SDS.utils.text.split_by('(&)', '&', '(', ')', '"')
        self.assertEqual(r, ['(&)', ])

        # should raise an exception for unclosed parentheses
        self.assertRaises(ValueError, SDS.utils.text.split_by, *[
                          '((()))))', ',', '(', ')', ""])

    def test_parse_command(self):
        # make sure the SDS.utils.text.parse_command splits the command correctly
        r = SDS.utils.text.parse_command('call(destination="1245",opt="X")')
        self.assertEqual(r, {"__name__": "call", "destination": "1245", "opt": "X"})

if __name__ == '__main__':
    unittest.main()
