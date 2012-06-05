#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os.path
import collections
import re
import argparse

import __init__

"""
This program extracts short sentences from a list of text files.

"""

def split_into_sentences(s):
  x = s.split(' ')

  if len(x) < 3:
    return []

  if len(x) < 10:
    return [s, ]

  x = s.split('.')

  return x

if __name__ == '__main__':
  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
    This program process extracts short sentences from a list of text files.

    """)


  parser.add_argument('--indir', action="store", default='./mkp_data',
                      help='an input directory with the text files files (default: ./mkp_data)')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose oputput')

  args = parser.parse_args()


  indir = args.indir
  verbose = args.verbose

  txt_files = glob.glob(os.path.join(indir,'*.txt'))

  r = []

  for fn in txt_files:
    print 'Processing file: ' + fn

    f = open(fn, 'r')

    for l in f:
      l = l.strip()
      l = re.split(r"[A-Z]+: ", l)

      if len(l) != 2:
        continue

      s = l[1].replace('-', '')
      s = s.replace('(', '')
      s = s.replace(')', '')
      s = s.replace('"', '')
      s = s.replace('  ', ' ')
      s = s.replace('  ', ' ')
      s = s.replace('…', ' ')

      if "ó ó" in s:
        continue

      s = s.strip()

      s = re.split(r'[\.!\?]', s)

      r.extend(s)

    f.close()

  for i in r:
    i = i.strip()
    i = i.replace('  ', ' ')
    i = i.replace('  ', ' ')
    ii = i.split(' ')
    if 4 < len(ii) < 10:
      print i
