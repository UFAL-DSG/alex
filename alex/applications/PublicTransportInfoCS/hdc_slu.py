#!/usr/bin/env python
# encoding: utf8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import autopath

from alex.components.asr.utterance import UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork
from alex.utils.czech_stemmer import cz_stem

# if there is a change in search parameters from_stop, to_stop, time, then
# reset alternatives


def _fill_utterance_values(abutterance, category, res):
    for _, value in abutterance.insts_for_type((category.upper(), )):
        if value == ("[OTHER]", ):
            continue

        res[category].append(value)


def _any_word_in(utterance, words):
    for alt_expr in cz_stem(words):
        if  alt_expr in utterance.utterance:
            return True

    return False


def _all_words_in(utterance, words):
    for alt_expr in cz_stem(words):
        if  alt_expr not in utterance.utterance:
            return False
    return True


def _phrase_in(utterance, words):
    return cz_stem(words) in utterance


class PTICSHDCSLU(SLUInterface):
    def __init__(self, preprocessing, cfg=None):
        super(PTICSHDCSLU, self).__init__(preprocessing, cfg)

    def parse_stop(self, abutterance, cn):
        """ Detects stops in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """
        preps_from = set(["z", "za", "ze", "od", "začátek", "začáteční",
                          "počáteční", "počátek", "výchozí", "start"])
        preps_to = set(["k", "do", "konec", "na", "konečná", "koncová",
                        "cílová", "cíl", "výstupní"])

        u = abutterance
        N = len(u)

        confirm = _phrase_in(u, ['jede', 'to']) or _phrase_in(u, ['odjíždí', 'to'])

        for i, w in enumerate(u):
            if w.startswith("STOP="):
                stop_name = w[5:]
                from_stop = False
                to_stop = False

                if i >= 2:
                    if not u[i - 1].startswith("STOP="):
                        if u[i - 2] in preps_from:
                            from_stop = True
                        elif u[i - 2] in preps_to:
                            to_stop = True

                if i >= 1:
                    if u[i - 1] in preps_from:
                        from_stop = True
                    elif u[i - 1] in preps_to:
                        to_stop = True

                if not from_stop and not to_stop:
                    if i <= N - 3:
                        if not u[i + 1].startswith("STOP="):
                            if u[i + 2] in preps_from:
                                to_stop = True
                            elif u[i + 2] in preps_to:
                                from_stop = True

                    if i <= N - 2:
                        if u[i + 1] in preps_from:
                            to_stop = True
                        elif u[i + 1] in preps_to:
                            from_stop = True

                if not from_stop and not to_stop:
                    if 1 <= i:
                        if u[i - 1].startswith('STOP'):
                            to_stop = True

                    if  i <= N - 2:
                        if u[i + 1].startswith('STOP'):
                            from_stop = True

                if confirm:
                    dat = "confirm"
                else:
                    dat = "inform"

                if from_stop and not to_stop:
                    cn.add(1.0, DialogueActItem(dat, "from_stop", stop_name))

                if not from_stop and to_stop:
                    cn.add(1.0, DialogueActItem(dat, "to_stop", stop_name))

                # backoff 1: add both from and to stop slots
                if from_stop and to_stop:
                    cn.add(0.501, DialogueActItem(dat, "from_stop", stop_name))
                    cn.add(0.499, DialogueActItem(dat, "to_stop", stop_name))

                # backoff 2: we do not know what slot it belongs to, let the DM
                # decide in the context resolution
                if ((not from_stop and not to_stop)
                        or (from_stop and to_stop)):
                    cn.add(0.501, DialogueActItem(dat, "", stop_name))
                    cn.add(0.499, DialogueActItem(dat, "", stop_name))

    def parse_time(self, abutterance, cn):
        """Detects the time in the input abstract utterance.

        :param abutterance:
        :param cn:
        """
        preps_in = set(["v", "čas"])

        u = abutterance
        N = len(u)

        for i, w in enumerate(u):
            if w.startswith("TIME="):
                time_value = w[5:]
                time = False

                if i >= 1:
                    if u[i - 1] in preps_in:
                        time = True

                if N == 1:
                    # if there is only one word in the utterance then suppose that it is time
                    time = True

                if time:
                    cn.add(1.0, DialogueActItem("inform", 'time', time_value))

    def parse_meta(self, utterance, cn):
        if (_any_word_in(utterance, ["ahoj",  "nazdar", "zdar", ]) or
                _all_words_in(utterance, ["dobrý",  "den"])):
            cn.add(1.0, DialogueActItem("hello"))

        if (_any_word_in(utterance,
                         ["nashledanou", "shledanou", "shle", "nashle",
                          "sbohem", "bohem", "zbohem", "zbohem", "konec",
                          "hledanou", "naschledanou"])):
            cn.add(1.0, DialogueActItem("bye"))

        if not _any_word_in(utterance, ["spojení", "zastávka", "stanice", "možnost"]):
            if _any_word_in(utterance, ["jiný", "jiné", "jiná", "další", "dál", "jiného"]):
                cn.add(1.0, DialogueActItem("reqalts"))

        if not (_any_word_in(utterance,
                             ["spojení", "zastávka", "stanice", "možnost"])):
            if (_any_word_in(utterance,
                             ["zopakovat",  "opakovat", "znov", "opakuj",
                              "zopakuj"])
                    or _phrase_in(utterance, ["ještě", "jedno"])):
                cn.add(1.0, DialogueActItem("repeat"))

        if _any_word_in(utterance, ["nápověda",  "pomoc", "help", "nevím", "nevim"]) or \
            _all_words_in(utterance, ["co", "říct"]) or \
            _all_words_in(utterance, ["co", "zeptat"]):
            cn.add(1.0, DialogueActItem("help"))

        if _any_word_in(utterance, ["ano",  "jo", "jasně"]):
            cn.add(1.0, DialogueActItem("affirm"))

        if _any_word_in(utterance, ["ne", "nejed"]):
            cn.add(1.0, DialogueActItem("negate"))

        if (_any_word_in(utterance,
                         ["díky", "dikec", "děkuji", "děkuju", "děkují"])):
            cn.add(1.0, DialogueActItem("thankyou"))

        if ((_any_word_in(utterance, ["od", "začít", ])
                and _any_word_in(utterance, ["začátku", "znov", ])
                or _any_word_in(utterance, ["restart", ])
                or _all_words_in(utterance, ["nové", "spojení"]))):
            cn.add(1.0, DialogueActItem("restart"))

        if _phrase_in(utterance, ["z", "centra"]) and not _any_word_in(utterance, ["ne", "nejed", "nechci"]):
            cn.add(1.0, DialogueActItem('inform','from_centre','true'))

        if _phrase_in(utterance, ["do", "centra"]) and not _any_word_in(utterance, ["ne", "nejed", "nechci"]):
            cn.add(1.0, DialogueActItem('inform','to_centre','true'))

        if _phrase_in(utterance, ["z", "centra"]) and _any_word_in(utterance, ["ne", "nejed", "nechci"]):
            cn.add(1.0, DialogueActItem('inform','from_centre','false'))

        if _phrase_in(utterance, ["do", "centra"]) and _any_word_in(utterance, ["ne", "nejed", "nechci"]):
            cn.add(1.0, DialogueActItem('inform','to_centre','false'))

        if _all_words_in(utterance, ["od", "to", "jede"]) or \
            _all_words_in(utterance, ["z", "jake", "jede"]) or \
            _all_words_in(utterance, ["z", "jaké", "jede"]) or \
            _all_words_in(utterance, ["jaká", "výchozí", ]) or \
            _all_words_in(utterance, ["kde", "začátek", ]) or \
            _all_words_in(utterance, ["odkud", "to", "jede"]) or \
            _all_words_in(utterance, ["odkud", "pojede"]) or \
            _all_words_in(utterance, ["od", "kud", "pojede"]):
            cn.add(1.0, DialogueActItem('request','from_stop'))

        if _all_words_in(utterance, ["kam", "to", "jede"]) or \
            _all_words_in(utterance, ["do", "jake", "jede"]) or \
            _all_words_in(utterance, ["do", "jaké", "jede"]) or \
            _all_words_in(utterance, ["co", "cíl", ]) or \
            _all_words_in(utterance, ["jaká", "cílová", ]) or \
            _all_words_in(utterance, ["kde", "konečná", ]) or \
            _all_words_in(utterance, ["kde", "konečná", ]) or \
            _all_words_in(utterance, ["kam", "pojede"]):
            cn.add(1.0, DialogueActItem('request','to_stop'))

        if _any_word_in(utterance, ["kolik", "jsou", "je"]) and \
            _any_word_in(utterance, ["přestupů", "přestupu", "přestupy", "stupňů", "přestup", "přestupku", "přestupky", "přestupků"]):
            cn.add(1.0, DialogueActItem('request','num_transfers'))

        if _any_word_in(utterance, ["spoj", "spojení", "možnost", "cesta", "zpoždění", "stažení"]):
            if _any_word_in(utterance, ["první", ]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "1"))

            if _any_word_in(utterance, ["druhé"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "2"))

            if _any_word_in(utterance, ["třetí"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "3"))

            if _any_word_in(utterance, ["čtvrté", "čtvrtá"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "4"))

            if _any_word_in(utterance, ["poslední", "znovu", "opakovat", "zopakovat"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "last"))

            if _any_word_in(utterance, ["další", "jiné", "následující"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

            if _any_word_in(utterance, ["předchozí", "před"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

    def parse_1_best(self, obs, verbose=False):
        """Parse an utterance into a dialogue act."""
        utterance = obs['utt']

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
