#!/usr/bin/env python
# coding=utf-8
#

"""
A collection of helper functions for generating English.
"""

from __future__ import unicode_literals

__author__ = "Martin Vejman"
__date__ = "2014"

_NUMBERS = {0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
            6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
            11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen',
            15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
            19: 'nineteen', 20: 'twenty', 30: 'thirty', 40: 'forty',
            50: 'fifty', 60: 'sixty', 70: 'seventy', 80: 'eighty',
            90: 'ninety', 100: 'hundred', 200: 'two hundred', 300: 'three hundred',
            400: 'four hundred', 500: 'five hundred', 600: 'six hundred', 700: 'seven hundred',
            800: 'eight hundred', 900: 'nine hundred', 1000: 'one thousand', 2000: 'two thousand',
            3000: 'three thousand', 4000: 'four thousand', 5000: 'five thousand',
            6000: 'six thousand', 7000: 'seven thousand', 8000: 'eight thousand', 9000: 'nine thousand'
}
_NUMBERS_ORD = {0:"zero", 1:"first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
                # nultý - zero/prime?
                7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth",
                13: "thirteenth", 14: "fourteenth", 15: "fifteenth", 16: "sixteenth", 17: "seventeenth",
                18: "eighteenth", 19: "nineteenth", 20: "twentieth", 30: "thirtieth", 40: "fortieth",
                50: "fiftieth", 60: "sixtieth", 70: "seventieth", 80: "eightieth", 90: "ninetieth",
                100: "hundredth", 200: "two hundredth", 300:"three hundredth", 400:"four hundredth",
                500: 'five hundredth', 600: 'six hundredth', 700: 'seven hundredth',800: 'eight hundredth',
                900: 'nine hundredth', 1000: 'one thousandth',
}


def word_for_number(number, ordinal=False):
    """\
    Returns a word given a number 1-100
    """
    # > 1000: composed of thousands
    if number > 1000 and number % 1000 != 0:
        return ' '.join((word_for_number((number / 1000) * 1000),
                         word_for_number(number % 1000, ordinal)))
    # > 100: composed of hundreds
    if number > 100 and number % 100 != 0:
        return ' '.join((word_for_number((number / 100) * 100),
                         word_for_number(number % 100, ordinal)))
    # > 20: composed of tens and ones
    if number > 20 and number % 10 != 0:
        return ' '.join((word_for_number((number / 10) * 10),
                         word_for_number(number % 10, ordinal)))

    if ordinal:
        return _NUMBERS_ORD[number]
    else:
        return _NUMBERS[number]

def every_word_for_number(number, ordinal=False, use_coupling=False):
    """
    params: ordinal - if set to True, it returns ordinal number (fifth rather than five etc).
            use_coupling if set to True, it returns number greater than 100 with "and" between hundreds and tens
                (two hundred and seventeen rather than two hundred seventeen).
    Returns a word given a number 1-100
    """
    # > 1000: composed of thousands
    if number > 1000 and number % 1000 != 0:
        return ' '.join((every_word_for_number((number / 1000) * 1000),
                         every_word_for_number(number % 1000, ordinal)))
    # > 100: composed of hunderds
    if number > 100 and number % 100 != 0:
        joiner = use_coupling and " and " or " "
        return joiner.join((every_word_for_number((number / 100) * 100),
                         every_word_for_number(number % 100, ordinal)))
    # > 20: composed of tens and ones
    if number > 20 and number % 10 != 0:
        return ' '.join((every_word_for_number((number / 10) * 10),
                         every_word_for_number(number % 10, ordinal)))

    return ordinal and _NUMBERS_ORD[number] or _NUMBERS[number]
