#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

from alex.components.nlg.tools.en import every_word_for_number

prefixes = {
    'st': 'saint',
    'st.': 'saint',
    'e': 'east',
    'w': 'west',
    'n': 'north',
    's': 'south',
    }

suffixes = {
    'ap': 'approach',
    'av': 'avenue',
    'av.': 'avenue',
    'ave': 'avenue',
    'avs': 'avenues',
    'bl': 'boulevard',
    'blvd': 'boulevard',
    'bklyn': 'brooklyn',
    'bx': 'bronx',
    'cir': 'circle',
    'ct': 'court',
    'ctr': 'center',
    'dr': 'drive',
    'dwy': 'driveway',
    'drwy': 'driveway',
    'e': 'east',
    'ent': 'entrance',
    'ep': 'expressway',
    'ex': 'expressway',
    'exp': 'expressway',
    'expy': 'expressway',
    'expwy': 'expressway',
    'ft': 'fort',
    'gdn': 'garden',
    'gdns': 'gardens',
    'hts': 'heights',
    'hway': 'highway',
    'hwy': 'highway',
    'hay': 'highway',
    'jct': 'junction',
    'ln': 'lane',
    'lp': 'loop',
    'mt': 'mount',
    'n': 'north',
    'opp': 'opp',
    'pk': 'park',
    'pkwy': 'parkway',
    'py': 'parkway',
    'pl': 'place',
    'plz': 'plaza',
    'pz': 'plaza',
    'qn': 'queens',
    'rd': 'road',
    'rd.': 'road',
    'rdwy': 'roadway',
    'rdy': 'roadway',
    'rt': 'route',
    's': 'south',
    'st': 'street',
    'st.': 'street',
    'st#': 'street',
    'sts': 'streets',
    'svc': 'service',
    'sq': 'square',
    'ter': 'terrace',
    'tp': 'turnpike',
    'tpke': 'turnpike',
    'tnl': 'tunnel',
    'w': 'west',
    '#': 'number ',
    }


def spell_if_number(word, use_coupling, ordinal=True):
    for suf in ['th', 'st', 'nd', 'rd', "'"]:
        if word.endswith(suf):
            word_stripped = word.rstrip(suf)
            if word_stripped.isdigit() and int(word_stripped) <= 1000:
                return every_word_for_number(int(word_stripped), ordinal, use_coupling)

    if word.startswith('#'):
        word = word.lstrip('#')
        if word.isdigit() and int(word) <= 1000:
            return 'number ' + every_word_for_number(int(word), False, use_coupling)

    if word.isdigit() and int(word) <= 1000:
        return every_word_for_number(int(word), ordinal, use_coupling)
    else:
        return word


def fix_ordinal(word):
    num_suff = ['th', 'st', 'nd', 'rd', ]
    if not word.isdigit():
        return word
    number = int(word)
    if number < 10 or number > 20:
        number %= 10
        if number < 4:
            return word + num_suff[number]
    return word + "th"


def expand(element, spell_numbers=True):

    words = element.lower().split()
    words[0] = prefixes.get(words[0], words[0])
    if spell_numbers:
        words[0] = spell_if_number(words[0], True)
    else:
        words[0] = fix_ordinal(words[0])
    words = [suffixes.get(w, w) for w in words]
    if spell_numbers:
        words = [spell_if_number(w, True, True) for w in words]
    else:
        words = [fix_ordinal(w) for w in words]

    return " ".join(words).lower()


def expand_stop(stop, spell_numbers=True):
    if stop is None:
        return None
    if '/' in stop:
        elements = stop.split('/')  # lexington av/63 street
        conjunction = ' and '
    elif '-' in stop:
        elements = stop.split('-')
        conjunction = ' , '
    elif '(' in stop:
        elements = stop.replace(')', '').split('(')  # cathedral pkwy (110 st)
        conjunction = ' on '

    elif '&' in stop:
        elements = stop.split('&')  # BARUCH INFORMATION & TECH BLDG
        conjunction = ' and '
    else:
        elements = [stop, ]
        conjunction = ' '

    expansion = [expand(el, spell_numbers) for el in elements]

    return conjunction.join(expansion)