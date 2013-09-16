#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import sys
import collections
import os.path

try:
    lm = sys.argv[1]
except IndexError as e:
    print "An ARPA N-gram language model needed"
    exit()

# load dictionary
f = open(lm, 'r')
gram = 0
for l in f:
    l = l.strip()

    if "1-grams:" in l:
        gram = 1
    if "2-grams:" in l:
        gram = 2

    l = l.split()

    if gram == 1 and len(l) > 1:
        print l[1]
