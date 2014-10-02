#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
from collections import defaultdict

from components.nlg.tools.en import every_word_for_number


borough_codes = {
    1: "Manhattan",
    2: "Bronx",
    3: "Brooklyn",
    4: "Queens",
    5: "Staten Island",
}

prefixes = {
    'ST': 'saint',
    'E': 'east',
    'W': 'west',
}

suffixes = {
    'Pkwy': 'parkway',
    'St': 'street',
    'ST': 'street',
    'Sts': 'streets',
    'Av': 'avenue',
    'AV': 'avenue',
    'Sq': 'square',
    'Hts': 'heights',
    'Rd': 'road',
    'Blvd': 'boulevard',
    'Tpke': 'turnpike',
    'Pl': 'place',
    'Ctr': 'center',

    'AVE-E': 'avenue east',
    '1/2': 'half',
    'PCT': 'PCT',
    'DRV': 'DRV',
    'BLDG': 'building',
}


def spell_if_number(word, use_coupeling, ordinal = True):
    if word.isdigit():
        return every_word_for_number(int(word), use_coupeling)
    else:
        return word

'''
use_coupling : and between ordinal numbers greater than 99 (two hundred and sixty fifth street)
'''
def expand(stop):
    words = stop.split()

    words[0] = prefixes.get(words[0], words[0])
    words[0] = spell_if_number(words[0], True)
    words = [suffixes.get(w, w) for w in words]
    words = [spell_if_number(w, False, False) for w in words]

    variants = [" ".join(words).lower(),]

    return variants


def get_column_index(header, caption, default):
    for i, h in enumerate(header.split(',')):
        if h == caption:
            return i
    return default


def is_street(line):
    if line.startswith('#') or not line:  # skip comments
        return False

    return True


def expand_cow_streets(file_name):
    stops = defaultdict(list)

    with codecs.open(file_name, 'r', 'UTF-8') as stopsFile:
        header = stopsFile.readline()

        for line in stopsFile:
            if not is_street(line):
                continue;

            full_street_name = line[3:34].strip();
            borough_index = int(line[1])
            borough = borough_codes.get(borough_index)

            #full_street_name.replace('-', ' ')
            #full_street_name.replace('&', ' and ')
            # if '/' in full_street_name and is_any_of_them_number:
            #     expand_numbers_devided_by_space_not_ordinally

            expansion = expand(full_street_name)
            # print(expansion)
            stops[full_street_name] = [" ".join(expansion), ]

            print (borough, full_street_name, stops[full_street_name])


def main():
    files_to_expand = ["/home/m2rtin/Desktop/transport/streets/snd14Ccow.txt", ]

    for raw_file in files_to_expand:
        expand_cow_streets(raw_file)
    #TODO - maybe group by tne number -> all street acronyms


if __name__ == '__main__':
    main()