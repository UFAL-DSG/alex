#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import sys

min_words = 4
max_words = 15
max_ppl = 400
max_oovs = 5
max_oovs_per = 0.3
max_zprobs = 2

in3 = collections.deque(maxlen=3)

def srilm_scores(d3):
    text = d3[0].split()
    l1 = d3[1].split()
    l2 = d3[2].split()
    WORDs = int(l1[2])
    OOVs = int(l1[4])
    ZPROBs = int(l2[0])
    PPL = float(l2[7]) if l2[7] != 'undefined' else 1e10

    return text, WORDs, OOVs, ZPROBs, PPL

f_in = sys.stdin

for in_l in f_in:
    in3.append(in_l)

    try:
        if 'zeroprobs' in in_l:
            text, WORDs, OOVs, ZPROBs, PPL = srilm_scores(in3)

            if WORDs >= min_words and \
               WORDs <= max_words and  \
               OOVs <= max_oovs and \
               float(OOVs) / WORDs <= max_oovs_per and \
               ZPROBs <= max_zprobs and \
               PPL < max_ppl:
                # print WORDs, OOVs, ZPROBs, PPL, ' '.join(text)
                print ' '.join(text)

    except:
        break