#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os.path
import collections
import re
import argparse

from collections import defaultdict

import __init__

"""
This program extracts short sentences from a list of text files.

"""

reject = ["Halo","Ať ","I ","Šak ","Ultimus","Rossum","Busmane","dušinko","V ","Oh, ",
"S ","Z ","Oh ","A i","RUR","Haha","plemeniti",
]

replace_by_empty_string = [', prosím vás,', ', ó hleďte,',', slečno Gloryová,', 'Brrr haha,',
]

replace_by_space = ['d5', ' hr hr', '  ',  '  '
]

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

  parser.add_argument('--indir', action="store", default='./texts',
                      help='an input directory with the text files files (default: ./texts)')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose oputput')

  args = parser.parse_args()


  indir = args.indir
  verbose = args.verbose

  txt_files = glob.glob(os.path.join(indir,'*.txt'))

  r = []

  for fn in txt_files:
    f = open(fn, 'r')

    for l in f:
      l = l.strip()
      l = re.split(r"[A-Z]+: ", l)

      if len(l) != 2:
        continue

      s = l[1].replace('-', '')
      s = s.replace('(', '')
      s = s.replace(')', '')
      s = s.replace(':', '')
      s = s.replace(';', '')
      s = s.replace('…', ' ')
      s = s.replace('"', '')
      s = s.replace('"', '')

      s = re.split(r'[\.!\?]', s)

      r.extend(s)

    f.close()

  r = [s for s in r if s != "" and s != " "]
  r1 = sorted(r)
  r2 = []
  for s in r1:
    ii = s.split(' ')
    if not (4 < len(ii) < 10):
      continue

    for x in replace_by_space:
      s = s.replace(x, ' ')
    s = s.strip()
    r2.append(s)

  r2 = sorted(r2)
  r3 = []
  for s in r2:
    for x in replace_by_empty_string:
      s = s.replace(x, '')

    for x in replace_by_space:
      s = s.replace(x, ' ')

    # remove duplciate words
    s = re.sub(r'\s(\w+)\s+\1', '\1', s)
    s = re.sub(r'^(\w+)\s+\1', '\1', s)

    s = s.strip()

    c = False
    for x in reject:
      if x in s:
        c = True
        break
    if c:
      continue


    if s.count(',') > 0:
      continue


#    print s
    s = re.sub(', Toni$', "", s)
    s = re.sub(', Ondro$', "", s)
    s = re.sub(', Heleno$', "", s)
    s = re.sub(', [^\ ]+$', "", s)
    s = re.sub(' Promiňte$', "", s)
    s = re.sub(", hm$", "", s)
    s = re.sub(r", že$", "", s)
    s = re.sub(r", viď$", "", s)
    s = re.sub(r", víš$", "", s)
    s = re.sub(r", ne$", "", s)
    s = re.sub(r"^A ", "", s)
    s = re.sub(r"^Fi, ", "", s)
    s = re.sub(r"^Gall ", "", s)
    s = re.sub(r"^Galle, ", "", s)
    s = re.sub(r"^Jirko, ", "", s)
    s = re.sub(r"^Harry, ", "", s)
    s = re.sub(r"^My my, ", "my", s)
    s = re.sub(r"^Ty, ", "", s)
    s = re.sub(r"^Ach [a-zA-Z]+,", "", s)
#    print s
#    print '-'

    s = s.strip()

    r3.append(s)

  r3 = sorted(r3)
  r4 = []
  for i in r3:
    i = i.strip()
    i = i.replace('  ', ' ')
    i = i.replace('  ', ' ')
    ii = i.split(' ')
    if 4 < len(ii) < 10:
      print i
      r4.append(i)


#  d = defaultdict(int)
#  for i in r4:
#    for ii in i:
#      d[ii] += 1
#
#
#  for k in sorted(d.keys()):
#    print k, ":", d[k]
#

