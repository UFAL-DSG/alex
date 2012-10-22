#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os.path

try:
    mfcn = sys.argv[1]
    subs = sys.argv[2]
except IndexError, e:
    exit()

mfcf = open(mfcn, 'r')
for l in mfcf:
    l = l.strip().split()

    fn = os.path.basename(l[1])
    l[1] = os.path.join(subs, fn)

    print ' '.join(l)

mfcf.close()
