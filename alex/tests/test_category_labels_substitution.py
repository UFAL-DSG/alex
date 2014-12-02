#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Made into a unit test, since it used to fail and Jenkins would not find about
# it.
# 2013-07-02 Matěj Korvas
if __name__ == '__main__':
    import autopath

import os.path
import unittest

from alex.components.asr.utterance import load_utterances
from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import load_das

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class TestCatlabSubstitution(unittest.TestCase):

    def test_catlab_substitution(self):
        utterances_dict = load_utterances(
            os.path.join(SCRIPT_DIR, 'resources', 'towninfo-train.trn'))
        semantics_dict = load_das(
            os.path.join(SCRIPT_DIR, 'resources', 'towninfo-train.sem'))

        cldb = CategoryLabelDatabase(
            os.path.join(SCRIPT_DIR, 'resources', 'database.py'))
        preprocessing = SLUPreprocessing(cldb)

        for k in semantics_dict:
            print '=' * 120
            print utterances_dict[k]
            print semantics_dict[k]

            utterance, da, category_labels = (
                preprocessing.values2category_labels_in_da(utterances_dict[k],
                                                        semantics_dict[k]))

            print '-' * 120
            print utterance
            print da
            print category_labels
            print '-' * 120

            full_utt = preprocessing.category_labels2values_in_utterance(
                utterance, category_labels)
            full_da = preprocessing.category_labels2values_in_da(
                da, category_labels)

            print full_utt
            print full_da


if __name__ == '__main__':
    unittest.main()
