#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

try:
    lm = sys.argv[1]
except IndexError:
    print "An ARPA n-gram language model needed."
    exit()

# Load the dictionary.
with open(lm, 'r') as f:
    gram = 0
    for line in f:
        if "1-grams:" in line:
            gram = 1
        if "2-grams:" in line:
            gram = 2

        line = line.split()

        if gram == 1 and len(line) > 1:
            print line[1]
