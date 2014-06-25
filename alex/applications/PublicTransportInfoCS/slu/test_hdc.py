#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import autopath

from alex.applications.PublicTransportInfoCS.slu.test import trained_slu_test, hdc_slu_test
from alex.components.asr.utterance import Utterance, UtteranceNBList

if __name__ == "__main__":
    # cheating experiment on all data using models trained on all data
    hdc_slu_test('./all.trn', Utterance, './all.trn.hdc.sem')
    hdc_slu_test('./all.asr', Utterance, './all.trn.hdc.sem')
    hdc_slu_test('./all.nbl', UtteranceNBList, './all.trn.hdc.sem')

    # regular experiment evaluating models trained on training data and evaluated on deb and test data
    # **WARNING** due to data sparsity the metrics on the dev and test data fluctuate a lot
    # therefore meaningful results can be only obtained using N-fold cross validation

    hdc_slu_test('./dev.trn', Utterance, './dev.trn.hdc.sem')
    hdc_slu_test('./dev.asr', Utterance, './dev.trn.hdc.sem')
    hdc_slu_test('./dev.nbl', UtteranceNBList, './dev.trn.hdc.sem')

    hdc_slu_test('./test.trn', Utterance, './test.trn.hdc.sem')
    hdc_slu_test('./test.asr', Utterance, './test.trn.hdc.sem')
    hdc_slu_test('./test.nbl', UtteranceNBList, './test.trn.hdc.sem')

