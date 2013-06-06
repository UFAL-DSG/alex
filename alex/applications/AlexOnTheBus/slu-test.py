#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path

import autopath


from alex.components.asr.utterance import load_utterances
from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import load_das, save_das, DialogueActHyp
from alex.components.slu.dailrclassifier import DAILogRegClassifier
from alex.corpustools.semscore import score
from alex.components.asr.utterance import Utterance

from aotb_preprocessing import AOTBSLUPreprocessing

cldb = CategoryLabelDatabase('./data/database.py')
pp = AOTBSLUPreprocessing(cldb)
pp.text_normalization_mapping += [
    (["ve"], ["v"]),
]

lr_classifier = DAILogRegClassifier(pp)
lr_classifier.load_model('./slu-lr-trn.model')

while 1:
    u = Utterance(raw_input().decode('utf8'))
    print lr_classifier.parse(u, verbose=2)