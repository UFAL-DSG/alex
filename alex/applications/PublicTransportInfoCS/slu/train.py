#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import autopath

from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
from alex.components.asr.utterance import Utterance, UtteranceNBList
from alex.components.slu.da import DialogueAct
from alex.components.slu.base import CategoryLabelDatabase
from alex.components.slu.dailrclassifier import DAILogRegClassifier
from alex.corpustools.wavaskey import load_wavaskey

def increase_weight(d, weight):
    new_d = {}
    for i in range(weight):
        for k in d:
            new_d["{k}v_{i}".format(k=k,i=i)] = d[k]

    d.update(new_d)

def train(fn_model,
          fn_transcription, constructor, fn_annotation,
          fn_bs_transcription, fn_bs_annotation,
          min_feature_count = 2,
          min_classifier_count = 2,
          limit = 100000):
    """
    Trains a SLU DAILogRegClassifier model.

    :param fn_model:
    :param fn_transcription:
    :param constructor:
    :param fn_annotation:
    :param limit:
    :return:
    """
    bs_utterances = load_wavaskey(fn_bs_transcription, Utterance, limit = limit)
    increase_weight(bs_utterances, min_feature_count+10)
    bs_das = load_wavaskey(fn_bs_annotation, DialogueAct, limit = limit)
    increase_weight(bs_das, min_feature_count+10)

    utterances = load_wavaskey(fn_transcription, constructor, limit = limit)
    das = load_wavaskey(fn_annotation, DialogueAct, limit = limit)

    utterances.update(bs_utterances)
    das.update(bs_das)

    cldb = CategoryLabelDatabase('../data/database.py')
    preprocessing = PTICSSLUPreprocessing(cldb)
    slu = DAILogRegClassifier(cldb, preprocessing, features_size=4)

    slu.extract_classifiers(das, utterances, verbose=True)
    slu.prune_classifiers(min_classifier_count = min_classifier_count)
    slu.print_classifiers()
    slu.gen_classifiers_data()
    slu.prune_features(min_feature_count = min_feature_count, verbose=True)

    slu.train(inverse_regularisation=1e1, verbose=True)

    slu.save_model(fn_model)

def main():
  min_feature_count = 1

  train('./dailogreg.trn.model.all', './all.trn', Utterance,       './all.trn.hdc.sem', './bootstrap.trn', './bootstrap.sem',
        min_feature_count = min_feature_count, min_classifier_count = 3)
  train('./dailogreg.asr.model.all', './all.asr', Utterance,       './all.trn.hdc.sem', './bootstrap.trn', './bootstrap.sem',
        min_feature_count = min_feature_count, min_classifier_count = 3)
  train('./dailogreg.nbl.model.all', './all.nbl', UtteranceNBList, './all.trn.hdc.sem', './bootstrap.trn', './bootstrap.sem',
        min_feature_count = min_feature_count, min_classifier_count = 3)

  train('./dailogreg.trn.model', './train.trn', Utterance,       './train.trn.hdc.sem', './bootstrap.trn', './bootstrap.sem',
        min_feature_count = min_feature_count, min_classifier_count = 3)
  train('./dailogreg.asr.model', './train.asr', Utterance,       './train.trn.hdc.sem', './bootstrap.trn', './bootstrap.sem',
        min_feature_count = min_feature_count, min_classifier_count = 3)
  train('./dailogreg.nbl.model', './train.nbl', UtteranceNBList, './train.trn.hdc.sem', './bootstrap.trn', './bootstrap.sem',
        min_feature_count = min_feature_count, min_classifier_count = 3)


if __name__ == '__main__':
  main()
