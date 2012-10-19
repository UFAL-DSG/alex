#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import sys
import collections
import os.path

pattern1, pattern2, pattern3, pattern4 = None, None, None, None

try:
    dctn = sys.argv[1]
    mlfn = sys.argv[2]
    scpn = sys.argv[3]
    dir  = sys.argv[4]
    pattern1 = sys.argv[5]
    pattern2 = sys.argv[6]
    pattern3 = sys.argv[7]
    pattern4 = sys.argv[8]
except IndexError, e:
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
    # load dictionary
    dctf = open(dctn, 'r')
    for l in dctf:
        l = l.strip()
        l = l.split()

        if len(l) > 0:
            dct[l[0]] = 1

    dctf.close()
except IOError, e:
    print e

    dict_test = False

    print "No dictionary will be used to remove any transcriptions"

mlf = []
mlf.append('#!MLF!#')
scp = []

for fn in fns:
    f = open(fn, 'r')
    l = f.readlines()
    l = ' '.join(l)

    l = l.strip()
    l = l.split()

    if dict_test:
        missing_word = False
        for w in l:
            if w not in dct:
                missing_word = True
                break
        if missing_word:
            print "Missing word in: ", fn, "word: ", w
            print "  - ", l
            continue

    new_fn = os.path.join(dir, os.path.basename(fn))
    scp.append(new_fn.replace('.wav.trn','.mfc'))

    mlf.append('"%s"' % new_fn.replace('.wav.trn','.lab'))
    for w in l:
        mlf.append('%s' % w)
    mlf.append('.')

    f.close()

mlff = open(mlfn,'w')
for l in mlf:
    mlff.write(l+'\n')
mlff.close()

scpf = open(scpn,'w')
for l in scp:
    scpf.write(l+'\n')
scpf.close()
