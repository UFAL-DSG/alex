#!/usr/bin/env python
# -*- coding: utf-8 -*-

import autopath

import random

from alex.components.asr.utterance import load_utterances, Utterance
from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import load_das, save_das, DialogueAct
from alex.components.slu.dailrclassifier import DAILogRegClassifier

from aotb_preprocessing import AOTBSLUPreprocessing

# Load data.
utterances = load_utterances('./data/train_slu.txt')
das = load_das('./data/train_slu.sem')

# Load processing data and configuration.
cldb = CategoryLabelDatabase('./data/database.py')
pp = AOTBSLUPreprocessing(cldb)
pp.text_normalization_mapping += [
    (["ve"], ["v"]),
]

utterances2 = {}
das2 = {}

def rand_db(slot):
    rk = random.choice(cldb.database[slot].keys())
    return rk, " ".join(random.choice(cldb.database[slot][rk]))

for (uk, utterance), da in zip(utterances.iteritems(), das.values()):
    new_utterance = utterance
    new_da = da

    for i in range(0):
        for slot in ['time', 'from', 'to']:
            slot_ph = "$%s$" %  slot
            if slot_ph in new_utterance.utterance:
                rv, rk = rand_db(slot)
                new_utterance = Utterance(str(new_utterance).replace(slot_ph, rk).decode('utf8'))
                new_da = DialogueAct(str(new_da).replace(slot_ph, rk).decode('utf8'))



        utterances2[uk + "." + str(i)] = new_utterance
        das2[uk + "." + str(i)] = new_da

    print new_da, new_utterance



# Prepare the classifier.
lr_learning = DAILogRegClassifier(pp)
lr_learning.extract_features(utterances, das)
lr_learning.prune_features(min_feature_count=0, verbose=True)
lr_learning.prune_classifiers(min_dai_count=0)
lr_learning.print_classifiers()

# Train and pickle the model.
lr_learning.train(verbose=True, calibrate=True)
lr_learning.save_model('./slu-lr-trn.model')
