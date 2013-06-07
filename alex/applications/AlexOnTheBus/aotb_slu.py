#!/usr/bin/python
# encoding: utf8

from __future__ import unicode_literals
from collections import defaultdict

import autopath

from alex.components.asr.utterance import Utterance
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork
from alex.utils.czech_stemmer import cz_stem


def _fill_utterance_values(abutterance, category, res):
    for _, value in abutterance.insts_for_type((category.upper(), )):
        if value == ("[OTHER]", ):
            continue

        res[category].append(value)

def _any_word_in(utterance, words):
    for alt_expr in words:
        if alt_expr in utterance.utterance:
            return True
    return False

def _all_words_in(utterance, words):
    for alt_expr in words:
        if alt_expr not in utterance.utterance:
            return False
    return True


class AOTBSLU(SLUInterface):
    def __init__(self, preprocessing, cfg=None):
        super(AOTBSLU, self).__init__(preprocessing, cfg)

        # self.helper_slu = DAILogRegClassifier(preprocessing)
        #self.helper_slu.load_model(
        #    cfg['SLU']['DAILogRegClassifier']['model'])

    def parse_stop(self, abutterance, cn):
        res = defaultdict(list)
        _fill_utterance_values(abutterance, 'stop', res)

        stop_name = None
        for slot, values in res.iteritems():
            for value in values:
                stop_name = u" ".join(value)
                break

        utt_set = set(abutterance)

        preps_from = set([u"z", u"za", u"ze", u"od", u"začátek"])
        preps_to = set([u"k", u"do", u"konec", u"na"])

        preps_from_used = preps_from.intersection(utt_set)
        preps_to_used = preps_to.intersection(utt_set)

        preps_from_in = len(preps_from_used) > 0
        preps_to_in = len(preps_to_used) > 0

        cn.add(1.0, DialogueActItem("inform", "stop", stop_name))

        if preps_from_in and not preps_to_in:
            cn.add(1.0,
                   DialogueActItem("inform", "from_stop", stop_name,
                                   attrs={'prep': next(iter(preps_from_used))})
                   )

        if not preps_from_in and preps_to_in:
            cn.add(1.0,
                   DialogueActItem("inform", "to_stop", stop_name,
                                   attrs={'prep': next(iter(preps_to_used))}))

    def parse_time(self, abutterance, cn):
        res = defaultdict(list)
        _fill_utterance_values(abutterance, 'time', res)

        for slot, values in res.iteritems():
            for value in values:
                cn.add(1.0, DialogueActItem("inform", slot, " ".join(value)))
                break

    def parse_meta(self, utterance, cn):

        if _any_word_in(utterance, [u"jiný", u"jiné", u"jiná", u"další",
                                      u"dál", u"jiného"]):
            cn.add(1.0, DialogueActItem("reqalts"))

        if _any_word_in(utterance, [u"děkuji", u"nashledanou", u"shledanou", u"shle", u"díky",
                                        u"sbohem", u"zdar"]):
            cn.add(1.0, DialogueActItem("bye"))

        if _any_word_in(utterance, [u"zopakovat",  u"opakovat", u"znovu", u"opakuj", u"zopakuj" ]) or \
            _all_words_in(utterance, [u"ještě",  u"jednou" ]):

            cn.add(1.0, DialogueActItem("repeat"))

        if _any_word_in(utterance, [u"napověda",  u"pomoc", u"znovu", ]):
            cn.add(1.0, DialogueActItem("help"))

    def parse(self, utterance, *args, **kwargs):
        if not isinstance(utterance, Utterance):
            utterance_1 = utterance.get_best_utterance()
        else:
            utterance_1 = utterance

        utt_norm = self.preprocessing.text_normalisation(utterance_1)

        abutterance, category_labels = (
            self.preprocessing.values2category_labels_in_utterance(utt_norm))

        res_cn = DialogueActConfusionNetwork()
        if 'STOP' in category_labels:
            self.parse_stop(abutterance, res_cn)
        elif 'TIME' in category_labels:
            self.parse_time(abutterance, res_cn)

        self.parse_meta(utt_norm, res_cn)

        return res_cn
