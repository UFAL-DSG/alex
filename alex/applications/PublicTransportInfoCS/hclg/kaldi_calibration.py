#!/usr/bin/env python
# encoding: utf-8
from __future__ import unicode_literals

"""
This script computes a calibration fucntion for KALDI ASR word posterior scores.

It assumes that relevant binary fst(s) already exists. These can be computed using

::
    cd .. && run_decode_indomain_kaldi.sh
    cd .. run_decode_indomain_kaldi_trn.sh

It also assumes that exists all_trn.txt which can be produced by

::
    cat ../lm/reference_transcription_dev.txt ../lm/reference_transcription_trn.txt > decoded_kaldi/all_trn.txt

Th

"""
if __name__ == '__main__':
    import autopath

import glob
import os
import fst
import codecs
import numpy as np
import scipy
from scipy.optimize import curve_fit
import pylab as P
from collections import defaultdict
from math import exp
import time

from alex.components.asr.utterance import Utterance
from alex.corpustools.wavaskey import save_wavaskey, load_wavaskey
from alex.utils.various import split_to_bins

def basename_dict(dct):
    d = {}

    for k in dct:
        d[os.path.basename(k)] = dct[k]

    return d

def load_lat(fn):
    lat = fst.read(fn)
    lat = fst.StdVectorFst(lat)

    return lat

def load_words(fn):
    words = []
    with codecs.open(fn, 'r', 'utf8') as f:
        for l in f:
            words.append(l.split()[0].strip())

    return words

def sigmoid(x, x0, k):
    y = 1 / (1 + np.exp(-k*(x-x0)))
    return y

def sig1(x, x0, a, b, c):
    return a*np.exp(b*(x-x0)) + c

def scores_distribution(wp_2_match):
    x = []
    s = []
    l = []
    n0 = 0
    n1 = 20
    max_n = 20
    for n in range(n0, n1):
        f0 = float(n) / max_n
        f1 = (n+1.0) / max_n

        match = [wpm[1] for wpm in wp_2_match if f0 < wpm[0] <= f1]

        if len(match):
            succ = sum(match) / len(match)
        else:
            succ = 0.0

        print f0, f1, len(match), succ

        x.append(f0)
        s.append(succ)
        l.append(float(len(match))/len(wp_2_match))

    xdata = [wpm[0] for wpm in wp_2_match]
    ydata = [wpm[1] for wpm in wp_2_match]
    popt, pcov = curve_fit(sigmoid, xdata, ydata)

    print popt

    fitx = np.linspace(0, 1, 50)
    fity = sigmoid(fitx, *popt)

    f = P.figure()
    p = f.add_subplot(2,1,1)
    p.bar(x, s, width=.6/(max_n))
    p.plot(fitx, fity)
    p.grid(True)

    p = f.add_subplot(2,1,2)
    p.bar(x, l, width=.6/(max_n), facecolor='green', alpha=0.75)
    p.grid(True)

    P.savefig('kaldi_calibration_scores_distribution.pdf')

def scores_equal_size_bins(wp_2_match):

    max_n = 100
    print "Split into equal size bins"
    wp_2_match_binned = split_to_bins(wp_2_match, len(wp_2_match)/max_n)
    # wp_2_match_binned[0][0][0] = 0.0

    # merge the same bins
    wp_2_match_binned_new = []
    for b in wp_2_match_binned:
        min = b[0][0]
        max = b[-1][0]

        if wp_2_match_binned[-1][0][0] == min and wp_2_match_binned[-1][-1][0] == max:
            wp_2_match_binned_new[-1].extend(b)
        else:
            wp_2_match_binned_new.append(b)

    wp_2_match_binned = wp_2_match_binned_new

    x = []
    s = []
    i = -1
    for b in wp_2_match_binned:
        min = b[0][0]
        max = b[-1][0]

        match = [wpm[1] for wpm in b]
        succ = sum(match) / len(match)
        # print "{min:.6e} -- {max:.6e} | {size} / {succ:.3f}".format(min=min, max=max, size=len(b), succ=succ)

        i += 1

        x.append(float(i))
        s.append(succ)

    xdata = [f for f in x]
    ydata = [f for f in s]

    sigma = [1.0 for f in x]
    sigma[-2] = 0.99
    sigma[-1] = 0.1

    popt, pcov = curve_fit(sig1, xdata, ydata, sigma = sigma, p0 = [0.0, 1.0, 0.0, 0.0] )

    print popt

    fitx = np.linspace(0, len(x), 50)
    fity = sig1(fitx, *popt)


    for xx, ss, f in zip(x, s, sig1(x, *popt)):
        print xx, ss, f

#    f = P.figure()
#    p = f.add_subplot(2,1,1)
#    p.bar(x, s)
#    # p = f.add_subplot(2,1,2)
#    p.plot(fitx,fity)
#    p.grid(True)

#    P.savefig('kaldi_calibration_scores_equal_size_bins.pdf')

    print "Calibration table"

    cal_list = []
    last_f = 2.0
    last_min = 2.0
    for b, f in reversed(zip(wp_2_match_binned, sig1(x, *popt))):
        min = b[0][0]
        max = b[-1][0]

        if last_f - f > 0.02:
            cal_list.append((min, last_min, f))
            print min, f
            last_f = f
            last_min = min
    else:
        print -2.0, f
        cal_list.append((-2.0, last_min, f))

    def find_approx(x):
        for i, (min, max, f) in enumerate(cal_list):
            if min <= x < max:
                return i, f

        print "ASR calibration warning: cannot map score."
        return x

    count = defaultdict(int)

    s = time.time()
    for wpm in wp_2_match:
        i, f = find_approx(wpm[0])
        count[i] += 1
    e = time.time()
    print "size {size} elapsed {time}".format(size=len(wp_2_match), time = e - s)

    pri_cal_list = []
    for i, x in enumerate(cal_list):
        pri_cal_list.append((count[i], x))

    pri_cal_list.sort()
    pri_cal_list.reverse()

    cal_list = [ x[1] for x in pri_cal_list]
    s = time.time()
    for wpm in wp_2_match:
        i, f = find_approx(wpm[0])
    e = time.time()
    print "size {size} elapsed {time}".format(size=len(wp_2_match), time = e - s)

    print "="*120
    print "The calibration table: insert it in the config"
    print "-"*120
    print repr(cal_list)

if __name__ == '__main__':

    reference = 'decoded_kaldi/all_trn.txt'
    trn_dict = load_wavaskey(reference, Utterance)
    trn_dict = basename_dict(trn_dict)

    fst_dir = 'decoded_kaldi'
    fst_fns = sorted(glob.glob(os.path.join(fst_dir, '*.fst')))

    words = load_words('models/words.txt')

    wp_2_match = []
    for i, fn in enumerate(fst_fns):
        print '='*120
        print i, fn

        ref = trn_dict[os.path.basename(fn).replace('fst','wav')]
        print unicode(ref)
        print '-'*120

        lat = load_lat(fn)

        for state in lat.states:
            for arc in state.arcs:
                if words[arc.ilabel] == '<eps>':
                    continue
                if '_' in words[arc.ilabel]:
                    continue

                print('{} -> {} ({}) / {} = {}'.format(state.stateid, arc.nextstate, words[arc.ilabel],
                                                       exp(-float(arc.weight)),
                                                       1.0 if [words[arc.ilabel],] in ref else 0.0))


                wp_2_match.append((exp(-float(arc.weight)), 1.0 if [words[arc.ilabel],] in ref else 0.0))


    wp_2_match.sort()

#    scores_distribution(wp_2_match)

    scores_equal_size_bins(wp_2_match)

    # print wp_2_match
