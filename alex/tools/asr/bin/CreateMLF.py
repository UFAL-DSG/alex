#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fdm=marker :

import glob
import sys
import collections
import os.path

# Read arguments.
#{{{
pats = list()

# Read the command line arguments.
try:
    dctn = sys.argv[1]
    pats = sys.argv[2:]
except IndexError:
    pass


try:
    dctn = sys.argv[1]
    mlfn = sys.argv[2]
    scpn = sys.argv[3]
    outdir = sys.argv[4]
    pats = sys.argv[5:]
except IndexError:
    pass

# Collect all filenames from the globs passed in as arguments.
fns = list()
for pat in pats:
    fns.extend(glob.iglob(pat))

# Load the dictionary.
dct = set()
try:
    with open(dctn, 'r') as dctf:
        for line in dctf:
            line = line.split()
            if line:
                dct.add(line[0])
except IOError as er:
    print "No dictionary will be used to remove transcriptions."
    pass
#}}}

# Initialise buffer-like variables for the output.
# `mlf_lines' will store a list of lines to write out to the `mlfn' file.
mlf_lines = []
mlf_lines.append('#!MLF!#')
# `scp_lines' will store a list of lines to write out to the `scpn' file.
scp_lines = []

# Process the input files.
#{{{
for fn in fns:
    with open(fn, 'r') as f:
        words = f.read().split()
        # If a dictionary has been specified,
        if dct:
            # check that all words are present there.
            missing_word = False
            for word in words:
                if word not in dct:
                    missing_word = True
                    break
            # Bail out on the first word in `f' missing from the dictionary.
            if missing_word:
                print "Missing word in: ", fn, "word: ", word
                print "  - ", words
                continue

        # Store the contents for the output files.
        new_fn = os.path.join(outdir, os.path.basename(fn))
        scp_lines.append(new_fn.replace('.wav.trn', '.mfc'))

        mlf_lines.append('"{0}"'.format(new_fn.replace('.wav.trn', '.lab')))
        for word in words:
            mlf_lines.append(word)
        mlf_lines.append('.')
#}}}

# Write out the .mlf and .scp files.
with open(mlfn, 'w') as mlff:
    for line in mlf_lines:
        mlff.write(line + '\n')

with open(scpn, 'w') as scpf:
    for line in scp_lines:
        scpf.write(line + '\n')
