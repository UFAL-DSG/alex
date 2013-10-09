#!/usr/bin/env python
# coding=utf-8
#

from __future__ import unicode_literals

import re

__author__ = "Ondřej Dušek"
__date__ = "2013"


def vocalize_prep(prep, following_word):
    """\
    Given a base for of a preposition and the form of the word following it,
    return the appropriate form (base or vocalized).

    Case insensitive; however, the returned vocalization is always lowercase.
    """
    lcprep = prep.lower()
    following_word = following_word.lower()
    if lcprep == 'k' and re.match('^(prospěch|příklad)', following_word):
        return prep + 'u'
    if lcprep == 'k' and re.match('^(k|g|sp|sn|zv|zm|sc|zl|sl|sk|zp|zk|šk|' +
                                  'zd|zt|zb|zr|sv|mn|vš|vs|ct|sj|dv|zř|zh|' +
                                  'vč|šp|lá|šť|mř|zc|št|vk|sta|vzn|stu|' +
                                  'vzd|smí|stě|dnu|vzo|sti|sty|sro|dnů|' +
                                  'sdr|sbl|sbí|čty|zná)', following_word):
        return prep + 'e'
    if lcprep == 'v' and re.match('^(v|f|st|sp|čt|sk|sv|kt|fr|fi|sl|sn|fu|' +
                                  'zl|fo|šv|zn|zp|šk|wa|ii|hř|dv|zd|sb|šp|' +
                                  'sh|št|zb|fa|fá|rw|zk|wi|tm|jm|we|fs|fy|' +
                                  'fó|žď|hv|gy|mz|žd|šl|gi|zh|sj|zt|žr|šr|' +
                                  'cv|sw|sro|sml|tří|tva|srá|obž|zví|psa|' +
                                  'smr|žlu|sca|zrů|sce|zvo|zme|mně$|mne$)',
                                  following_word):
        return prep + 'e'
    if lcprep == 's' and re.match('^(s|z|kt|vz|vš|mn|šk|že|čt|šv|št|ps|vs|' +
                                  'šp|ži|cm|ža|ct|cv|dž|šl|še|bý|čle|jmě|' +
                                  'ple|šam|lst|prs|dvě|dře|7|17$|1\d\d\D?)',
                                  following_word):
        return prep + 'e'
    if lcprep == 'z' and re.match('^(s|z|kt|dn|šk|vs|šv|vš|št|šu|dř|mz|ži|' +
                                  'tm|kb|šp|pé|ša|kč|hv|nk|ši|rt|lh|ký|ža|' +
                                  'lv|šl|žď|žl|hry|vzd|tří|rom|jmě|šes|' +
                                  'mne|řet|hři|lan|žel|pan|wil|dou|thp|' +
                                  'pak|půt|cih|brá|hrd|mik|idy|psů|mst|' +
                                  'mag|vas|4|7|17|1\d\d\D?)', following_word):
        return prep + 'e'
    return prep


_NUMBERS = {0: 'nula', 1: 'jeden', 2: 'dva', 3: 'tři', 4: 'čtyři', 5: 'pět',
            6: 'šest', 7: 'sedm', 8: 'osm', 9: 'devět', 10: 'deset',
            11: 'jedenáct', 12: 'dvanáct', 13: 'třináct', 14: 'čtrnáct',
            15: 'patnáct', 16: 'šestnáct', 17: 'sedmnáct', 18: 'osmnáct',
            19: 'devatenáct', 20: 'dvacet', 30: 'třicet', 40: 'čtyřicet',
            50: 'padesát', 60: 'šedesát', 70: 'sedmdesát', 80: 'osmdesát',
            90: 'devadesát', 100: 'sto'}


_FORMS = {'jeden': {'jeden': ['M1', 'I1', 'M5', 'I5', 'I4'],
                    'jedna': ['F1', 'F5'],
                    'jedné': ['F2', 'F3', 'F6'],
                    'jedním': ['M7', 'I7', 'N7'],
                    'jednoho': ['M4', 'M2', 'I2', 'N2'],
                    'jednom': ['M6', 'I6', 'N6'],
                    'jednomu': ['M3', 'I3', 'N3'],
                    'jedno': ['N1', 'N4', 'N5'],
                    'jednou': ['F7'],
                    'jednu': ['F4']},
          'dva': {'dva': ['M1', 'M4', 'I1', 'I4', 'I5', 'M5'],
                  'dvěma': ['M7', 'I7', 'N7', 'F7', 'M3', 'I3', 'F3', 'N3'],
                  'dvě': ['F1', 'F4', 'F5', 'N1', 'N4', 'N5'],
                  'dvou': ['M2', 'I2', 'N2', 'F2', 'M6', 'I6', 'N6', 'F6']},
          'tři': {'tři': ['1', '4', '5'],
                  'tří': ['2'],
                  'třemi': ['7'],
                  'třem': ['3'],
                  'třech': ['6']},
          'čtyři': {'čtyři': ['1', '4', '5'],
                    'čtyř': ['2'],
                    'čtyřem': ['3'],
                    'čtyřech': ['6'],
                    'čtyřmi': ['7']}}

# inverted _FORMS
_INFLECT = {}
for num, forms in _FORMS.iteritems():
    _INFLECT[num] = {}
    for form, categs in forms.iteritems():
        for categ in categs:
            _INFLECT[num][categ] = form


def word_for_number(number, categ='M1'):
    """\
    Returns a word given a number 1-100 (in the given gender + case).
    Gender (M, I, F, N) and case (1-7) are given concatenated.
    """
    # > 20: composed of tens and ones
    if number > 20 and number % 10 != 0:
        # 21, 31... - "1" has no declension
        if number % 10 == 1:
            return ' '.join((word_for_number((number / 10) * 10, categ),
                             'jedna'))
        # other numbers are OK
        return ' '.join((word_for_number((number / 10) * 10, categ),
                         word_for_number(number % 10, categ)))
    # 0 = no declension
    if number == 0:
        return _NUMBERS[0]
    if number > 2 and len(categ) > 1:
        categ = categ[1]
    if number <= 4:
        return _INFLECT[_NUMBERS[number]][categ]
    num_word = _NUMBERS[number]
    if categ in ['2', '3', '6', '7']:
        if number == 9:
            num_word = num_word[:-2] + 'íti'
        else:
            num_word += 'i'
    return num_word
