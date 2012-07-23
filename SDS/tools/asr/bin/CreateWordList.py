#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import sys
import collections

patern1, patern2, patern3, patern4 = None, None, None, None

try:
  dctn = sys.argv[1]
  pattern1 = sys.argv[2]
  pattern2 = sys.argv[3]
  pattern3 = sys.argv[4]
  pattern4 = sys.argv[5]
except IndexError:
  pass

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
  dict_test = False

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
  if dict_test and w in dct:
    print w
  else:
    print w
