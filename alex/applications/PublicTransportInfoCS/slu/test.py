#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os.path
import codecs
import autopath

from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceConfusionNetwork
from alex.components.slu.base import CategoryLabelDatabase
from alex.components.slu.dailrclassifier import DAILogRegClassifier
from alex.corpustools.wavaskey import load_wavaskey, save_wavaskey
from alex.corpustools.semscore import score

cldb = CategoryLabelDatabase('../data/database.py')
preprocessing = PTICSSLUPreprocessing(cldb)
slu = DAILogRegClassifier(cldb, preprocessing)


def trained_slu_test(fn_model, fn_input, constructor, fn_reference):
    """
    Tests a SLU DAILogRegClassifier model.

    :param fn_model:
    :param fn_input:
    :param constructor:
    :param fn_reference:
    :return:
    """
    print "="*120
    print "Testing: ", fn_model, fn_input, fn_reference
    print "-"*120

    slu.load_model(fn_model)

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

        da_confnet = slu.parse(obs, verbose=False)

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
            slu.parse(obs, verbose=True)

    if 'trn' in fn_model:
        fn_sem = os.path.basename(fn_input)+'.model.trn.sem.out'
    elif 'asr' in fn_model:
        fn_sem = os.path.basename(fn_input)+'.model.asr.sem.out'
    elif 'nbl' in fn_model:
        fn_sem = os.path.basename(fn_input)+'.model.nbl.sem.out'
    else:
        fn_sem = os.path.basename(fn_input)+'.XXX.sem.out'

    save_wavaskey(fn_sem, parsed_das)

    f = codecs.open(os.path.basename(fn_sem)+'.score', 'w+', encoding='UTF-8')
    score(fn_reference, fn_sem, True, f)
    f.close()

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

    fn_sem = os.path.basename(fn_input)+'.hdc.slu.sem.out'

    save_wavaskey(fn_sem, parsed_das)

    f = codecs.open(os.path.basename(fn_sem)+'.score', 'w+', encoding='UTF-8')
    score(fn_reference, fn_sem, True, f)
    f.close()

if __name__ == "__main__":

    # cheating experiment on all data using models trained on all data
    hdc_slu_test('./all.trn', Utterance, './all.trn.hdc.sem')
    hdc_slu_test('./all.asr', Utterance, './all.trn.hdc.sem')
    hdc_slu_test('./all.nbl', Utterance, './all.trn.hdc.sem')
    trained_slu_test('./dailogreg.trn.model.all', './all.trn', Utterance, './all.trn.hdc.sem')
    trained_slu_test('./dailogreg.asr.model.all', './all.asr', Utterance, './all.trn.hdc.sem')
    trained_slu_test('./dailogreg.nbl.model.all', './all.nbl', UtteranceNBList, './all.trn.hdc.sem')

    # regular experiment evaluating models trained on training data and evaluated on deb and test data
    # **WARNING** due to data sparsity the metrics on the dev and test data fluctuate a lot
    # therefore meaning full results can be only obtained using N-fold cross validation

    trained_slu_test('./dailogreg.trn.model', './dev.trn', Utterance, './dev.trn.hdc.sem')
    trained_slu_test('./dailogreg.trn.model', './dev.asr', Utterance, './dev.trn.hdc.sem')
    trained_slu_test('./dailogreg.trn.model', './dev.nbl', UtteranceNBList, './dev.trn.hdc.sem')

    trained_slu_test('./dailogreg.trn.model', './test.trn', Utterance, './test.trn.hdc.sem')
    trained_slu_test('./dailogreg.trn.model', './test.asr', Utterance, './test.trn.hdc.sem')
    trained_slu_test('./dailogreg.trn.model', './test.nbl', UtteranceNBList, './test.trn.hdc.sem')


    trained_slu_test('./dailogreg.asr.model', './dev.trn', Utterance, './dev.trn.hdc.sem')
    trained_slu_test('./dailogreg.asr.model', './dev.asr', Utterance, './dev.trn.hdc.sem')
    trained_slu_test('./dailogreg.asr.model', './dev.nbl', UtteranceNBList, './dev.trn.hdc.sem')

    trained_slu_test('./dailogreg.asr.model', './test.trn', Utterance, './test.trn.hdc.sem')
    trained_slu_test('./dailogreg.asr.model', './test.asr', Utterance, './test.trn.hdc.sem')
    trained_slu_test('./dailogreg.asr.model', './test.nbl', UtteranceNBList, './test.trn.hdc.sem')

    trained_slu_test('./dailogreg.nbl.model', './dev.trn', Utterance, './dev.trn.hdc.sem')
    trained_slu_test('./dailogreg.nbl.model', './dev.asr', Utterance, './dev.trn.hdc.sem')
    trained_slu_test('./dailogreg.nbl.model', './dev.nbl', UtteranceNBList, './dev.trn.hdc.sem')

    trained_slu_test('./dailogreg.nbl.model', './test.trn', Utterance, './test.trn.hdc.sem')
    trained_slu_test('./dailogreg.nbl.model', './test.asr', Utterance, './test.trn.hdc.sem')
    trained_slu_test('./dailogreg.nbl.model', './test.nbl', UtteranceNBList, './test.trn.hdc.sem')
