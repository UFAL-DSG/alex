#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
if __name__ == "__main__":
    import autopath

from alex.applications.PublicTransportInfoCS.slu.dainnclassifier.test import trained_slu_test
from alex.components.asr.utterance import Utterance, UtteranceNBList

if __name__ == "__main__":
    # regular experiment evaluating models trained on training data and evaluated on deb and test data
    # **WARNING** due to data sparsity the metrics on the dev and test data fluctuate a lot
    # therefore meaningful results can be only obtained using N-fold cross validation

    trained_slu_test('./dainn.trn.model', '../dev.trn', Utterance, '../dev.trn.hdc.sem')

    trained_slu_test('./dainn.trn.model', '../test.trn', Utterance, '../test.trn.hdc.sem')

    trained_slu_test('./dainn.asr.model', '../dev.asr', Utterance, '../dev.trn.hdc.sem')

    trained_slu_test('./dainn.asr.model', '../test.asr', Utterance, '../test.trn.hdc.sem')

    trained_slu_test('./dainn.nbl.model', '../dev.nbl', UtteranceNBList, '../dev.trn.hdc.sem')

    trained_slu_test('./dainn.nbl.model', '../test.nbl', UtteranceNBList, '../test.trn.hdc.sem')

    # cheating experiment on all data using models trained on all data
    # though these models are used for live system
    trained_slu_test('./dainn.trn.model.all', '../all.trn', Utterance, '../all.trn.hdc.sem')
    trained_slu_test('./dainn.asr.model.all', '../all.asr', Utterance, '../all.trn.hdc.sem')
    trained_slu_test('./dainn.nbl.model.all', '../all.nbl', UtteranceNBList, '../all.trn.hdc.sem')

