#!/usr/bin/python
# encoding: utf8

from __future__ import unicode_literals
from collections import defaultdict

import autopath

from alex.components.asr.utterance import Utterance, UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork, merge_slu_confnets
from alex.utils.czech_stemmer import cz_stem


def _fill_utterance_values(abutterance, category, res):
    for _, value in abutterance.insts_for_type((category.upper(), )):
        if value == ("[OTHER]", ):
            continue

        res[category].append(value)

def _any_word_in(utterance, words):
    for alt_expr in words:
        if  cz_stem(alt_expr) in utterance.utterance:
            return True
    return False

def _all_words_in(utterance, words):
    for alt_expr in words:
        if  cz_stem(alt_expr) not in utterance.utterance:
            return False
    return True


class AOTBSLU(SLUInterface):
    def __init__(self, preprocessing, cfg=None):
        super(AOTBSLU, self).__init__(preprocessing, cfg)

    def parse_stop(self, abutterance, cn):
        preps_from = set([u"z", u"za", u"ze", u"od", u"začátek"])
        preps_to = set([u"k", u"do", u"konec", u"na"])

        u = abutterance
        N = len(u)

        for i, w in enumerate(u):
            if w.startswith("STOP="):
                stop_name = w[5:]
                from_stop = False
                to_stop = False

                if i >= 2:
                    if not u[i-1].startswith("STOP="):
                        if u[i-2] in preps_from:
                            from_stop = True
                        elif u[i-2] in preps_to:
                            to_stop = True

                if i >= 1:
                    if u[i-1] in preps_from:
                        from_stop = True
                    elif u[i-1] in preps_to:
                        to_stop = True

                if not from_stop and not to_stop:
                    if i <= N - 3:
                        if not u[i+1].startswith("STOP="):
                            if u[i+2] in preps_from:
                                to_stop = True
                            elif u[i+2] in preps_to:
                                from_stop = True

                    if i <= N - 2:
                        if u[i+1] in preps_from:
                            to_stop = True
                        elif u[i+1] in preps_to:
                            from_stop = True

                if not from_stop and not to_stop:
                    if 1 <= i:
                        if u[i-1].startswith('STOP'):
                            to_stop = True

                    if  i <= N - 2:
                        if u[i+1].startswith('STOP'):
                            from_stop = True

                if from_stop and not to_stop:
                    cn.add(1.0, DialogueActItem("inform", "from_stop", stop_name))

                if not from_stop and to_stop:
                    cn.add(1.0, DialogueActItem("inform", "to_stop", stop_name))

                # backoff 1: add both from and to stop slots
                if from_stop and to_stop:
                    cn.add(0.501, DialogueActItem("inform", "from_stop", stop_name))
                    cn.add(0.499, DialogueActItem("inform", "to_stop", stop_name))

                # backoff 2: we do not know what slot it belongs to, let the DM decide in
                # the context resolution
                if not from_stop and not to_stop or \
                    from_stop and to_stop:
                    cn.add(0.501, DialogueActItem("inform", "", stop_name))
                    cn.add(0.499, DialogueActItem("inform", "", stop_name))


    def parse_time(self, abutterance, cn):
        res = defaultdict(list)
        _fill_utterance_values(abutterance, 'time', res)

        for slot, values in res.iteritems():
            for value in values:
                cn.add(1.0, DialogueActItem("inform", slot, " ".join(value)))
                break

    def parse_meta(self, utterance, cn):

        if _any_word_in(utterance, [u"ahoj",  u"nazdar", u"zdar", ]) or \
            _all_words_in(utterance, [u"dobrý",  u"den" ]):
            cn.add(1.0, DialogueActItem("hello"))

        if _any_word_in(utterance, [u"děkuji", u"nashledanou", u"shledanou", u"shle", u"nashle", u"díky",
            u"sbohem", u"zbohem", u"konec"]):
            cn.add(1.0, DialogueActItem("bye"))

        if _any_word_in(utterance, [u"jiný", u"jiné", u"jiná", u"další",
                                      u"dál", u"jiného"]):
            cn.add(1.0, DialogueActItem("reqalts"))

        if _any_word_in(utterance, [u"zopakovat",  u"opakovat", u"znovu", u"opakuj", u"zopakuj" ]) or \
            _all_words_in(utterance, [u"ještě",  u"jednou" ]):

            cn.add(1.0, DialogueActItem("repeat"))

        if _any_word_in(utterance, [u"nápověda",  u"pomoc", ]):
            cn.add(1.0, DialogueActItem("help"))

    def parse_1_best(self, utterance, verbose=False):
        """Parse an utterance into a dialogue act.
        """
        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        if verbose:
            print 'Parsing utterance "{utt}".'.format(utt=utterance)

        if self.preprocessing:
            # the text normalisation performs stemming
            utterance = self.preprocessing.text_normalisation(utterance)

            abutterance, category_labels = self.preprocessing.values2category_labels_in_utterance(utterance)
            if verbose:
                print 'After preprocessing: "{utt}".'.format(utt=abutterance)
                print category_labels
        else:
            category_labels = dict()

        res_cn = DialogueActConfusionNetwork()
        if 'STOP' in category_labels:
            self.parse_stop(abutterance, res_cn)
        elif 'TIME' in category_labels:
            self.parse_time(abutterance, res_cn)

        self.parse_meta(utterance, res_cn)

        if not res_cn:
            res_cn.add(1.0, DialogueActItem("other"))

        return res_cn

    def parse_nblist(self, utterance_list):
        """Parse N-best list by parsing each item in the list and then merging
        the results."""

        if len(utterance_list) == 0:
            return DialogueActConfusionNetwork()

        confnet_hyps = []
        for prob, utt in utterance_list:
            if "__other__" == utt:
                confnet = DialogueActConfusionNetwork()
                confnet.add(1.0, DialogueActItem("other"))
            else:
                confnet = self.parse_1_best(utt)

            confnet_hyps.append((prob, confnet))

            # print prob, utt
            # confnet.prune()
            # confnet.sort()
            # print confnet

        confnet = merge_slu_confnets(confnet_hyps)
        confnet.prune()
        confnet.sort()

        return confnet

    def parse_confnet(self, confnet, verbose=False):
        """Parse the confusion network by generating an N-best list and parsing
        this N-best list."""

        nblist = confnet.get_utterance_nblist(n=40)
        sem = self.parse_nblist(nblist)

        return sem
