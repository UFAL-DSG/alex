#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os.path

try:
    mfcn = sys.argv[1]
    subs = sys.argv[2]
except IndexError, e:
    exit()

with open(mfcn, 'r') as mfcf:
    for line in mfcf:
        line = line.strip().split()

        fn = os.path.basename(line[1])
        line[1] = os.path.join(subs, fn)

        print ' '.join(line)
