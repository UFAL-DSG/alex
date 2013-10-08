#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os.path
import codecs
import autopath

import test as trained_slu_test
from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceConfusionNetwork

def hdc_slu_test(fn_input, constructor, fn_reference):
    """
    Tests a SLU DAILogRegClassifier model.

    :param fn_model:
    :param fn_input:
    :param constructor:
    :param fn_reference:
    :return:
    """
    print "="*120
    print "Testing HDC SLU: ", fn_input, fn_reference
    print "-"*120

    from alex.components.slu.base import CategoryLabelDatabase
    from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
    from alex.applications.PublicTransportInfoCS.hdc_slu import PTICSHDCSLU
    from alex.corpustools.wavaskey import load_wavaskey, save_wavaskey
    from alex.corpustools.semscore import score

    cldb = CategoryLabelDatabase('../data/database.py')
    preprocessing = PTICSSLUPreprocessing(cldb)
    hdc_slu = PTICSHDCSLU(preprocessing)

    test_utterances = load_wavaskey(fn_input, constructor, limit=100000)

    parsed_das = {}
    for utt_key, utt in sorted(test_utterances.iteritems()):
        if isinstance(utt, Utterance):
            obs = {'utt': utt}
        elif isinstance(utt, UtteranceNBList):
            obs = {'utt_nbl': utt}
        else:
            raise BaseException('Unsupported observation type')

        print '-' * 120
        print "Observation:"
        print utt_key, " ==> "
        print unicode(utt)

        da_confnet = hdc_slu.parse(obs, verbose=False)

        print "Conf net:"
        print unicode(da_confnet)

        da_confnet.prune()
        dah = da_confnet.get_best_da_hyp()

        print "1 best: "
        print unicode(dah)

        parsed_das[utt_key] = dah.da

        if 'CL_' in str(dah.da):
            print '*' * 120
            print utt
            print dah.da
            hdc_slu.parse(obs, verbose=True)

    fn_sem = os.path.basename(fn_input)+'.hdc_slu.sem.out'

    save_wavaskey(fn_sem, parsed_das)

    f = codecs.open(os.path.basename(fn_sem)+'.score', 'w+', encoding='UTF-8')
    score(fn_reference, fn_sem, True, f)
    f.close()

trained_slu_test.test('./dailogreg.trn.model', './bootstrap.trn', Utterance, './bootstrap.sem')
trained_slu_test.test('./dailogreg.asr.model', './bootstrap.trn', Utterance, './bootstrap.sem')
trained_slu_test.test('./dailogreg.nbl.model', './bootstrap.trn', Utterance, './bootstrap.sem')

hdc_slu_test('./bootstrap.trn', Utterance, './bootstrap.sem')
