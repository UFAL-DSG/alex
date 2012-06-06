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

    s = s.replace(', prosím vás,', '')
    s = s.replace('  ', ' ')
    s = s.replace('  ', ' ')
    s = s.strip()
    r2.append(s)

  r2 = sorted(r2)
  r3 = []
  for s in r2:
    s = s.replace(', prosím vás,', '')
    s = s.replace(', ó hleďte,', '')
    s = s.replace(', slečno Gloryová,', '')
    s = s.replace('d5', ' ')
    s = s.replace(' hr hr', ' ')
    s = s.replace('Brrr haha,', '')
    s = s.replace('  ', ' ')
    s = s.replace('  ', ' ')
    s = s.strip()

    if "ó ó" in s:
      continue
    if "Halo" in s:
      continue
    if "Ať " in s:
      continue
    if "I " in s:
      continue
    if "Šak " in s:
      continue
    if "Ultimus" in s:
      continue
    if "Rossum" in s:
      continue
    if "Busmane" in s:
      continue
    if "V " in s:
      continue
    if "Oh, " in s:
      continue
    if "S " in s:
      continue
    if "Z " in s:
      continue
    if "Oh " in s:
      continue
    if "A i" in s:
      continue
    if "RUR" in s:
      continue
    if "Haha" in s:
      continue
    if s.count(',') > 1:
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


  d = defaultdict(int)
  for i in r4:
    for ii in i:
      d[ii] += 1


  for k in sorted(d.keys()):
    print k, ":", d[k]

