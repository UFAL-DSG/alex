#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import sys

# Initialisation.
dctn = '-'  # This is a special value for this argument, meaning no dictionary
            # should be used.
pats = list()

# Read the command line arguments.
try:
    dctn = sys.argv[1]
    pats = sys.argv[2:]
except IndexError:
    pass

dct = set()
# Load the dictionary.
if dctn != '-':
    try:
        with open(dctn, 'r') as dctf:
            for line in dctf:
                line = line.split()
                if line:
                    dct.add(line[0])
    except IOError:
        pass

# Collect all filenames from the globs passed in as arguments.
fns = list()
for pat in pats:
    fns.extend(glob.iglob(pat))

# Read all words from all the files.
word_set = set()
for fn in fns:
    with open(fn, 'r') as f:
        for line in f:
            word_set.update(line.split())

# Filter the words by the dictionary if one was provided.
word_list = sorted(word_set.intersection(dct) if dct else word_set)

# Print out all the words.
for word in word_list:
    print word
