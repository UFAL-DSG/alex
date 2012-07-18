#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import sys
import collections

patern1, patern2, patern3, patern4 = None, None, None, None

try:
  pattern1 = sys.argv[1]
  pattern2 = sys.argv[2]
  pattern3 = sys.argv[3]
  pattern4 = sys.argv[4]
except IndexError:
  pass
  
fns = glob.glob(pattern1)
if patern2:
  fns.extend(glob.glob(pattern2))
if patern3:
  fns.extend(glob.glob(pattern3))
if patern4:
  fns.extend(glob.glob(pattern4))

word_list = collections.defaultdict(int)
for fn in fns:
  f = open(fn, 'r')
  for l in f:
    l = l.strip()
    l = l.split()

    for w in l:
      word_list[w] += 1
      
  f.close()
  
word_list = sorted(word_list.keys())

for w in word_list:
    print w