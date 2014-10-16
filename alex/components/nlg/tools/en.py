#!/usr/bin/env python
# coding=utf-8
#

"""
A collection of helper functions for generating English.
"""

from __future__ import unicode_literals

__author__ = "Martin Vejman"
__date__ = "2014"

#
# def vocalize_prep(prep, following_word):
#     """\
#     Given a base for of a preposition and the form of the word following it,
#     return the appropriate form (base or vocalized).
#
#     Case insensitive; however, the returned vocalization is always lowercase.
#     """
#     lcprep = prep.lower()
#     following_word = following_word.lower()
#     if lcprep == 'k' and re.match('^(prospěch|příklad)', following_word):
#         return prep + 'u'
#     if lcprep == 'k' and re.match('^(k|g|sp|sn|zv|zm|sc|zl|sl|sk|zp|zk|šk|' +
#                                   'zd|zt|zb|zr|sv|mn|vš|vs|ct|sj|dv|zř|zh|' +
#                                   'vč|šp|lá|šť|mř|zc|št|vk|sta|vzn|stu|' +
#                                   'vzd|smí|stě|dnu|vzo|sti|sty|sro|dnů|' +
#                                   'sdr|sbl|sbí|čty|zná)', following_word):
#         return prep + 'e'
#     # exceptions 'v tř...' (town names) -- otherwise 've tř...' in all cases
#     if lcprep == 'v' and re.match('^(třine?c|třebíč|třebo[nň]|třeš[tť]|' +
#                                   'třebenic|třebechovic|třemoše?n)',
#                                   following_word, re.IGNORECASE):
#         return prep
#     if lcprep == 'v' and re.match('^(v|f|st|sp|čt|sk|sv|kt|fr|fi|sl|sn|fu|' +
#                                   'zl|fo|šv|zn|zp|šk|wa|ii|hř|dv|zd|sb|šp|' +
#                                   'sh|št|zb|fa|fá|rw|zk|wi|tm|jm|we|fs|fy|' +
#                                   'fó|žď|hv|gy|mz|žd|šl|gi|zh|sj|zt|žr|šr|' +
#                                   'cv|sw|tř|sro|sml|tva|srá|obž|zví|psa|' +
#                                   'smr|žlu|sca|zrů|sce|zvo|zme|mně$|mne$)',
#                                   following_word):
#         return prep + 'e'
#     if lcprep == 's' and re.match('^(s|z|kt|vz|vš|mn|šk|že|čt|šv|št|ps|vs|' +
#                                   'šp|ži|cm|ža|ct|cv|dž|šl|še|bý|čle|jmě|' +
#                                   'ple|šam|lst|prs|dvě|dře|7|17$|1\d\d\D?)',
#                                   following_word):
#         return prep + 'e'
#     if lcprep == 'z' and re.match('^(s|z|kt|dn|šk|vs|šv|vš|št|šu|dř|mz|ži|' +
#                                   'tm|kb|šp|pé|ša|kč|hv|nk|ši|rt|lh|ký|ža|' +
#                                   'lv|šl|žď|žl|hry|vzd|tří|rom|jmě|šes|' +
#                                   'mne|řet|hři|lan|žel|pan|wil|dou|thp|' +
#                                   'pak|půt|cih|brá|hrd|mik|idy|psů|mst|' +
#                                   'mag|vas|4|7|17|1\d\d\D?)', following_word):
#         return prep + 'e'
#     return prep


_NUMBERS = {0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
            6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
            11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen',
            15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
            19: 'nineteen', 20: 'twenty', 30: 'thirty', 40: 'fourty',
            50: 'fifty', 60: 'sixty', 70: 'seventy', 80: 'eighty',
            90: 'ninety', 100: 'hundred', 200: 'two hundred', 300: 'three hundred',
            400: 'four hundred', 500: 'five hundred', 600: 'six hundred', 700: 'seven hundred',
            800: 'eihgt hundred', 900: 'nine hundred', 1000: 'one thousand', 2000: 'two thousand',
            3000: 'three thousand', 4000: 'four thousand', 5000: 'five thousand',
            6000: 'six thousand', 7000: 'seven thousand', 8000: 'eight thousand', 9000: 'nine thousand'
}
_NUMBERS_ORD = {0:"zero", 1:"first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
                # nultý - zero/prime?
                7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth",
                13: "thirteenth", 14: "fourteenth", 15: "fifteenth", 16: "sixteenth", 17: "seventeenth",
                18: "eighteenth", 19: "nineteenth", 20: "twentieth", 30: "thirtieth", 40: "fourtieth",
                50: "fiftieth", 60: "sixtieth", 70: "seventieth", 80: "eightieth", 90: "ninetieth",
                100: "hundredth", 200: "two hundredth", 300:"three hundredth", 400:"fourhundredth",
                500: 'five hundredth', 600: 'six hundredth', 700: 'seven hundredth',800: 'eihgt hundredth',
                900: 'nine hundredth', 1000: 'one thousandth',
}


# _FORMS = {'jeden': {'jeden': ['M1', 'I1', 'M5', 'I5', 'I4'],
#                     'jedna': ['F1', 'F5'],
#                     'jedné': ['F2', 'F3', 'F6'],
#                     'jedním': ['M7', 'I7', 'N7'],
#                     'jednoho': ['M4', 'M2', 'I2', 'N2'],
#                     'jednom': ['M6', 'I6', 'N6'],
#                     'jednomu': ['M3', 'I3', 'N3'],
#                     'jedno': ['N1', 'N4', 'N5'],
#                     'jednou': ['F7'],
#                     'jednu': ['F4']},
#           'dva': {'dva': ['M1', 'M4', 'I1', 'I4', 'I5', 'M5'],
#                   'dvěma': ['M7', 'I7', 'N7', 'F7', 'M3', 'I3', 'F3', 'N3'],
#                   'dvě': ['F1', 'F4', 'F5', 'N1', 'N4', 'N5'],
#                   'dvou': ['M2', 'I2', 'N2', 'F2', 'M6', 'I6', 'N6', 'F6']},
#           'tři': {'tři': ['1', '4', '5'],
#                   'tří': ['2'],
#                   'třemi': ['7'],
#                   'třem': ['3'],
#                   'třech': ['6']},
#           'čtyři': {'čtyři': ['1', '4', '5'],
#                     'čtyř': ['2'],
#                     'čtyřem': ['3'],
#                     'čtyřech': ['6'],
#                     'čtyřmi': ['7']},
#           'sto': {'sto': ['1', '4', '5'],
#                   'sta': ['2'],
#                   'stu': ['3', '6'],
#                   'stem': ['7']},
#           'tisíc': {'tisíc': ['1', '4', '5'],
#                     'tisíce': ['2'],
#                     'tisíci': ['3', '6'],
#                     'tisícem': ['7']}}
#
# # inverted _FORMS
# _INFLECT = {}
# for num, forms in _FORMS.iteritems():
#     _INFLECT[num] = {}
#     for form, categs in forms.iteritems():
#         for categ in categs:
#             _INFLECT[num][categ] = form


def word_for_number(number, ordinary = False):
    """\
    Returns a word given a number 1-100
    """
    # > 1000: composed of thousands
    if number > 1000 and number % 1000 != 0:
        return ' '.join((word_for_number((number / 1000) * 1000),
                         word_for_number(number % 1000, ordinary)))
    # > 100: composed of hunderds
    if number > 100 and number % 100 != 0:
        return ' '.join((word_for_number((number / 100) * 100),
                         word_for_number(number % 100, ordinary)))
    # > 20: composed of tens and ones
    if number > 20 and number % 10 != 0:
        return ' '.join((word_for_number((number / 10) * 10),
                         word_for_number(number % 10, ordinary)))

    if ordinary:
        return _NUMBERS_ORD[number]
    else:
        return _NUMBERS[number]

def every_word_for_number(number, ordinary = False, use_coupling = False):
    """
    params: ordinary - if set to True, it returns ordinal of the number (fifth rather than five etc).
            use_coupling if set to True, it returns number greater than 100 with "and" between hundreds and tens
                (two hundred and seventeen rather than two hundred seventeen).
    Returns a word given a number 1-100
    """
    # > 1000: composed of thousands
    if number > 1000 and number % 1000 != 0:
        return ' '.join((every_word_for_number((number / 1000) * 1000),
                         every_word_for_number(number % 1000, ordinary)))
    # > 100: composed of hunderds
    if number > 100 and number % 100 != 0:
        joiner = use_coupling and " and " or " "
        return joiner.join((every_word_for_number((number / 100) * 100),
                         every_word_for_number(number % 100, ordinary)))
    # > 20: composed of tens and ones
    if number > 20 and number % 10 != 0:
        return ' '.join((every_word_for_number((number / 10) * 10),
                         every_word_for_number(number % 10, ordinary)))

    return ordinary and _NUMBERS_ORD[number] or _NUMBERS[number]


# class CzechTemplateNLGPostprocessing(TemplateNLGPostprocessing):
#     """Postprocessing filled in NLG templates for Czech.
#
#     Currently, this class only handles preposition vocalization.
#     """
#
#     def __init__(self):
#         super(CzechTemplateNLGPostprocessing, self).__init__()
#
#     def postprocess(self, nlg_text):
#         return self.vocalize_prepos(nlg_text)
#
#     def vocalize_prepos(self, text):
#         """\
#         Vocalize prepositions in the utterance, i.e. 'k', 'v', 'z', 's'
#         are changed to 'ke', 've', 'ze', 'se' if appropriate given the
#         following word.
#
#         This is mainly needed for time expressions, e.g. "v jednu hodinu"
#         (at 1:00), but "ve dvě hodiny" (at 2:00).
#         """
#         def pairwise(iterable):
#             a = iter(iterable)
#             return itertools.izip(a, a)
#         parts = re.split(r'\b([vkzsVKZS]) ', text)
#         text = parts[0]
#         for prep, follow in pairwise(parts[1:]):
#             text += vocalize_prep(prep, follow) + ' ' + follow
#         return text