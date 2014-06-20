#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import autopath

from alex.applications.PublicTransportInfoCS.slu.test import trained_slu_test, hdc_slu_test
from alex.components.asr.utterance import Utterance, UtteranceNBList

if __name__ == "__main__":
    # cheating experiment on all data using models trained on all data
    trained_slu_test('./dailogreg.trn.model.all', './all.trn', Utterance, './all.trn.hdc.sem')
    trained_slu_test('./dailogreg.asr.model.all', './all.asr', Utterance, './all.trn.hdc.sem')
    trained_slu_test('./dailogreg.nbl.model.all', './all.nbl', UtteranceNBList, './all.trn.hdc.sem')

    # regular experiment evaluating models trained on training data and evaluated on deb and test data
    # **WARNING** due to data sparsity the metrics on the dev and test data fluctuate a lot
    # therefore meaningful results can be only obtained using N-fold cross validation

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
