#!/usr/bin/env python
# -*- coding: utf-8 -*-

import __init__

from alex.components.asr.utterance import load_utterances
from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import load_das

if __name__ == '__main__':
    utterances_dict = load_utterances('./resources/towninfo-train.trn')
    semantics_dict = load_das('./resources/towninfo-train.sem')

    cldb = CategoryLabelDatabase('./resources/database.py')
    preprocessing = SLUPreprocessing(cldb)

    for k in semantics_dict:
        print '=' * 120
        print utterances_dict[k]
        print semantics_dict[k]

        utterance, da, category_labels = (preprocessing
           .values2category_labels_in_da(utterances_dict[k],
                                         semantics_dict[k]))

        print '-' * 120
        print utterance
        print da
        print category_labels
        print '-' * 120

        full_utterance = (preprocessing
                          .category_labels2values_in_utterance(
                              utterance, category_labels))
        full_da = preprocessing.category_labels2values_in_da(da,
                                                             category_labels)

        print full_utterance
        print full_da
