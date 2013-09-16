#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fdm=marker :

import glob
import sys
import collections
import os.path

# Read arguments.
#{{{
pattern1, pattern2, pattern3, pattern4 = None, None, None, None

try:
    dctn = sys.argv[1]
    mlfn = sys.argv[2]
    scpn = sys.argv[3]
    outdir = sys.argv[4]
    pattern1 = sys.argv[5]
    pattern2 = sys.argv[6]
    pattern3 = sys.argv[7]
    pattern4 = sys.argv[8]
except IndexError as e:
    pass

fns = glob.glob(pattern1)
if pattern2:
    fns.extend(glob.glob(pattern2))
if pattern3:
    fns.extend(glob.glob(pattern3))
if pattern4:
    fns.extend(glob.glob(pattern4))


dict_test = True
try:
    dct = {}
    # Load the dictionary.
    dctf = open(dctn, 'r')
    for line in dctf:
        words = line.strip().split()
        if len(words) > 0:
            dct[words[0]] = 1
    dctf.close()
except IOError as e:
    print e
    dict_test = False
    print "No dictionary will be used to remove any transcriptions."
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
        lines = f.readlines()
        lines = ' '.join(lines)

        words = lines.strip().split()

        # If a dictionary has been specified,
        if dict_test:
            # check that all words are present there.
            missing_word = False
            for w in words:
                if w not in dct:
                    missing_word = True
                    break
            # Bail out on the first word in `f' missing from the dictionary.
            if missing_word:
                print "Missing word in: ", fn, "word: ", w
                print "  - ", words
                continue

        # Store the contents for the output files.
        new_fn = os.path.join(outdir, os.path.basename(fn))
        scp_lines.append(new_fn.replace('.wav.trn', '.mfc'))

        mlf_lines.append('"{0}"'.format(new_fn.replace('.wav.trn', '.lab')))
        for w in words:
            mlf_lines.append(w)
        mlf_lines.append('.')
#}}}

# Write out the .mlf and .scp files.
with open(mlfn, 'w') as mlff:
    for line in mlf_lines:
        mlff.write(line + '\n')

with open(scpn, 'w') as scpf:
    for line in scp_lines:
        scpf.write(line + '\n')
