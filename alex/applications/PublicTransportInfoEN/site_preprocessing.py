#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

from alex.components.nlg.tools.en import every_word_for_number

prefixes = {
    'st':'saint',
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
    'bx': 'bronx',
    'cir': 'circle',
    'ct': 'court',
    'ctr': 'center',
    'dr': 'drive',
    'dwy': 'driveway',
    'drwy': 'driveway',
    'e': 'east',
    'ent': 'entrance',
    'ep' : 'expressway',
    'ex' : 'expressway',
    'exp' : 'expressway',
    'expy' : 'expressway',
    'expwy': 'expressway',
    'ft' : 'fort',
    'gdn': 'garden',
    'gdns': 'gardens',
    'hts': 'heights',
    'hway': 'highway',
    'hwy': 'highway',
    'hay': 'highway',
    'jct':'junction',
    'ln': 'lane',
    'lp': 'loop',
    'mt': 'mount',
    'n' : 'north',
    'opp': 'opp',
    'pk': 'park',
    'pkwy': 'parkway',
    'py': 'parkway',
    'pl': 'place',
    'plz': 'plaza',
    'pz': 'plaza',
    'qn': 'queens',
    'rd': 'road',
    'rdwy': 'roadway',
    'rdy': 'roadway',
    's': 'south',
    'st': 'street',
    'st.': 'street',
    'sts': 'streets',
    'svc': 'service',
    'sq': 'square',
    'ter': 'terrace',
    'tp': 'turnpike',
    'tpke': 'turnpike',
    'tnl': 'tunnel',
    'w': 'west',
    '#' : 'number ',
    }

def spell_if_number(word, use_coupling, ordinal=True):
    for suf in ['th', 'st', 'nd', 'rd']:
        if word.endswith(suf):
            word_stripped = word.rstrip(suf)
            if word_stripped.isdigit():
                return every_word_for_number(int(word_stripped), ordinal, use_coupling)

    if word.startswith('#'):
        word = word.lstrip('#')
        if word.isdigit():
            return 'number ' + every_word_for_number(int(word), False, use_coupling)

    if word.isdigit():
        return every_word_for_number(int(word), ordinal, use_coupling)
    else:
        return word

def expand(element):

    words = element.lower().split()
    words[0] = prefixes.get(words[0], words[0])
    words[0] = spell_if_number(words[0], True)
    words = [suffixes.get(w, w) for w in words]
    words = [spell_if_number(w, True, True) for w in words]

    return " ".join(words).lower()

def expand_stop(stop):
    if stop is None:
        return None
    if '/' in stop:
        elements = stop.split('/') # lexington av/63 street
        conjunction = ' at '
    elif '-' in stop:
        elements = stop.split('-')
        conjunction = ' and '
    elif '(' in stop:
        elements = stop.replace(')', '').split('(') # cathedral pkwy (110 st)
        conjunction = ' on '

    elif '&' in stop:
        elements = stop.split('&') # BARUCH INFORMATION & TECH BLDG
        conjunction = ' and '
    else:
        elements = [stop, ]
        conjunction = ' '

    expansion = [expand(el) for el in elements]

    return conjunction.join(expansion)