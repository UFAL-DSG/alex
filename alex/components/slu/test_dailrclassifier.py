# encoding: utf8
import os

from unittest import TestCase
from alex.components.slu.dailrclassifier import DAILogRegClassifier

from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.asr.utterance import Utterance, UtteranceNBList
from alex.components.slu.da import DialogueAct, DialogueActItem

class TestDAILogRegClassifier(TestCase):
    def test_parse_X(self):
        cldb = CategoryLabelDatabase()
        class db:
            database = {
                "task": {
                    "find_connection": ["najít spojení", "najít spoj", "zjistit spojení",
                                        "zjistit spoj", "hledám spojení", 'spojení', 'spoj',
                                       ],
                    "find_platform": ["najít nástupiště", "zjistit nástupiště", ],
                    'weather': ['pocasi', ],
                },
                "number": {
                    "1": ["jednu"]
                },
                "time": {
                    "now": ["nyní", "teď", "teďka", "hned", "nejbližší", "v tuto chvíli", "co nejdřív"],
                },
            }

        cldb.load(db_mod=db)

        preprocessing = SLUPreprocessing(cldb)
        clf = DAILogRegClassifier(cldb, preprocessing, features_size=4)

        # Train a simple classifier.
        das = {
            '1': DialogueAct('inform(task=weather)'),
            '2': DialogueAct('inform(time=now)'),
            '3': DialogueAct('inform(task=weather)'),
        }
        utterances = {
            '1': Utterance('pocasi'),
            '2': Utterance('hned'),
            '3': Utterance('jak bude'),
        }
        clf.extract_classifiers(das, utterances, verbose=False)
        clf.prune_classifiers(min_classifier_count=0)
        clf.gen_classifiers_data(min_pos_feature_count=0,
                                 min_neg_feature_count=0,
                                 verbose2=False)

        clf.train(inverse_regularisation=1e1, verbose=False)

        # Parse some sentences.
        utterance_list = UtteranceNBList()
        utterance_list.add(0.7, Utterance('pocasi'))
        utterance_list.add(0.7, Utterance('pocasi jak bude'))
        utterance_list.add(0.2, Utterance('hned'))

        da_confnet = clf.parse_X(utterance_list, verbose=False)


        self.assertTrue(da_confnet.get_prob(DialogueActItem(dai='inform(task=weather)')) > 0.5)
        self.assertTrue(da_confnet.get_prob(DialogueActItem(dai='inform(time=now)')) < 0.5)