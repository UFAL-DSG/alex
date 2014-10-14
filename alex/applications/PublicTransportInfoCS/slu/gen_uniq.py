#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import autopath
import codecs
import sys

from alex.corpustools.wavaskey import save_wavaskey
from alex.components.slu.base import CategoryLabelDatabase
from alex.components.asr.utterance import Utterance
from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
from alex.applications.PublicTransportInfoCS.hdc_slu import PTICSHDCSLU

"""
Uses HDC SLU to add DA annotations to input from uniq.trn file (by default, can be changed by supplying a filename as argument) and outputs them into uniq.trn.sem.tmp (in the format of uniq.trn.sem)
"""

def main():

    cldb = CategoryLabelDatabase('../data/database.py')
    preprocessing = PTICSSLUPreprocessing(cldb)
    slu = PTICSHDCSLU(preprocessing)
    abstract_only = False

    fn_uniq_trn_sem = 'uniq.trn.sem.tmp'

    if len(sys.argv) < 2:
        fn_uniq_trn = 'uniq.trn'
    else:
        fn_uniq_trn = sys.argv[1]

    print "Processing input from file", fn_uniq_trn
    uniq_trn = codecs.open(fn_uniq_trn, "r", encoding='utf8')
    uniq_trn_sem = {}
    for line in uniq_trn:
        wav_key, utterance = line.split(" => ",2)
        if abstract_only:
            utterance = slu.preprocessing.normalise_utterance(utterance)
            abutterance, _ = slu.abstract_utterance(utterance)
            annotation = abutterance
        else:
            da = slu.parse_1_best({'utt':Utterance(utterance)}).get_best_da()
            annotation = da
        uniq_trn_sem[wav_key] = utterance.rstrip() + " <=> " + annotation

    print "Saving output to file", fn_uniq_trn_sem
    save_wavaskey(fn_uniq_trn_sem, uniq_trn_sem)


if __name__ == '__main__':
    main()
