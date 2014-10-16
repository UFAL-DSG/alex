#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
from collections import defaultdict

def extract_state_codes(file_codes):
    codes = defaultdict(list)
    with codecs.open(file_codes, 'r', 'UTF-8') as file:
        for line in file:
            if line.startswith('#') or not line: # skip comments
                continue

            pair = line.split('\t'); # state \t code

            codes[pair[1].strip()] = pair[

                0].strip()
    return codes


def unfold_state_codes(file_to_unfold, state_codes):
    states = defaultdict(list)
    with codecs.open(file_to_unfold, 'r', 'UTF-8') as file:
        for line in file:
            # skip comments
            if line.startswith('#') or not line:
                continue

            #city\tlatitude|longitude   |state code
            line = line.strip()
            state_code = line.split('|')[-1]
            state = state_codes[state_code]
            states[line] = state
    return states


def main():

    file_to_unfold = "/home/m2rtin/Desktop/transport/cities/cities_locations.tsv"
    file_codes = "/home/m2rtin/Desktop/transport/cities/state.codes.txt"

    file_out = "/home/m2rtin/alex/alex/applications/PublicTransportInfoEN/data/w.cities_locations.tsv.txt"

    state_codes = extract_state_codes(file_codes)

    with codecs.open(file_out, 'w', 'UTF-8') as output:
        expansion = unfold_state_codes(file_to_unfold, state_codes)
        for key in expansion:
            print >> output, key.rsplit('|',1)[0] + '|' + expansion[key]


if __name__ == '__main__':
    main()
