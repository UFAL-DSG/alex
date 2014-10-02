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

            line = line.strip()
            pair = line.split('\t'); # city \t state code

            state_code = pair[1]
            state = state_codes[state_code]
            states[line] = state
    return states


def main():

    file_to_unfold = "/home/m2rtin/Desktop/transport/cities/cities.state.codes.txt"
    file_codes = "/home/m2rtin/Desktop/transport/cities/state.codes.txt"

    file_out = "/home/m2rtin/alex/alex/applications/PublicTransportInfoEN/data/w.states_cities.tsv.txt"

    state_codes = extract_state_codes(file_codes)

    with codecs.open(file_out, 'w', 'UTF-8') as output:
        expansion = unfold_state_codes(file_to_unfold, state_codes)
        for key in expansion:
            print >> output, expansion[key] + '\t' + key.split('\t')[0]


if __name__ == '__main__':
    main()
