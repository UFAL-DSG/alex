#!/usr/bin/env python
# encoding: utf8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

from alex.components.asr.utterance import UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork

# if there is a change in search parameters from_stop, to_stop, time, then
# reset alternatives

def _any_word_in(utterance, words):
    for alt_expr in words:
        if  alt_expr in utterance.utterance:
            return True

    return False


def _all_words_in(utterance, words):
    for alt_expr in words:
        if  alt_expr not in utterance.utterance:
            return False
    return True


def _phrase_in(utterance, words):
    return words in utterance


class PTICSHDCSLU(SLUInterface):
    def __init__(self, preprocessing, cfg=None):
        super(PTICSHDCSLU, self).__init__(preprocessing, cfg)

    def __repr__(self):
        return "PTICSHDCSLU({preprocessing}, {cfg})".format(preprocessing=self.preprocessing, cfg=self.cfg)

    def parse_stop(self, abutterance, cn):
        """ Detects stops in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """
        preps_from = set(["z", "za", "ze", "od", "začátek", "začáteční",
                          "počáteční", "počátek", "výchozí", "start"])
        preps_to = set(["k", "do", "konec", "na", "konečná", "koncová",
                        "cílová", "cíl", "výstupní"])
        fillers_from = set(["start", "stojím", "jsem" ])
        fillers_to = set(["cíl",])

        u = abutterance
        N = len(u)

        confirm = _phrase_in(u, ['jede', 'to']) or _phrase_in(u, ['odjíždí', 'to']) or _phrase_in(u, ['je', 'výchozí',])
        deny = _phrase_in(u, ['nechci', 'jet']) or _phrase_in(u, ['nechci', 'odjíždět'])

        for i, w in enumerate(u):
            if w.startswith("STOP="):
                stop_name = w[5:]
                from_stop = False
                to_stop = False
                stop_decided = False

                if stop_name == "Čím":
                    # just ignore this stop
                    continue

                if i >= 3:
                    if not u[i - 2].startswith("STOP=") and not u[i - 1].startswith("STOP="):
                        if u[i - 3] in fillers_from and u[i - 2] == 'na':
                            from_stop = True
                            stop_decided = True
                        elif u[i - 3] in fillers_to and u[i - 2] == 'na':
                            to_stop = True
                            stop_decided = True
                        if u[i - 3] in preps_from:
                            from_stop = True
                            stop_decided = True
                        elif u[i - 3] in preps_to:
                            to_stop = True
                            stop_decided = True

                if not stop_decided and i >= 2:
                    if not u[i - 1].startswith("STOP="):
                        if u[i - 2] in fillers_from and u[i - 1] == 'na':
                            from_stop = True
                            stop_decided = True
                        elif u[i - 2] in fillers_to and u[i - 1] == 'na':
                            to_stop = True
                            stop_decided = True
                        elif u[i - 2] in preps_from:
                            from_stop = True
                            stop_decided = True
                        elif u[i - 2] in preps_to:
                            to_stop = True
                            stop_decided = True

                if not stop_decided and i >= 1:
                    if u[i - 1] in preps_from:
                        from_stop = True
                        stop_decided = True
                    elif u[i - 1] in preps_to:
                        to_stop = True
                        stop_decided = True

                if not stop_decided:
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
                elif deny:
                    dat = "deny"
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
                if ((not from_stop and not to_stop) or \
                        (from_stop and to_stop)):
                    cn.add(0.501, DialogueActItem(dat, "", stop_name))
                    cn.add(0.499, DialogueActItem(dat, "", stop_name))

    def parse_time(self, abutterance, cn):
        """Detects the time in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance
        N = len(u)

        preps_in = set(["v", "čas", "o", "po", "před", "kolem"])

        confirm = _phrase_in(u, ['jede', 'to'])
        deny = _phrase_in(u, ['nechci', 'ne'])

        for i, w in enumerate(u):
            if w.startswith("TIME="):
                value = w[5:]
                time = False

                if i >= 1:
                    if u[i - 1] in preps_in:
                        time = True

                if confirm:
                    dat = "confirm"
                elif deny:
                    dat = "deny"
                else:
                    dat = "inform"

                if time:
                    cn.add(1.0, DialogueActItem(dat, 'time', value))

    def parse_time_rel(self, abutterance, cn):
        """Detects the relative time in the input abstract utterance.

        :param abutterance:
        :param cn:ce
        """

        u = abutterance
        N = len(u)

        preps_in = set(["za", ])

        confirm = _phrase_in(u, ['jede', 'to'])
        deny = _phrase_in(u, ['nechci', 'ne'])

        for i, w in enumerate(u):
            if w.startswith("TIME_REL="):
                value = w[9:]
                time = False

                if i >= 1:
                    if u[i - 1] in preps_in:
                        time = True

                if value == "now" and not _phrase_in(u, ['no','a',]):
                    time = True

                if confirm:
                    dat = "confirm"
                elif deny:
                    dat = "deny"
                else:
                    dat = "inform"

                if time:
                    cn.add(1.0, DialogueActItem(dat, 'time_rel', value))

    def parse_date_rel(self, abutterance, cn):
        """Detects the relative date in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance

        confirm = _phrase_in(u, ['jede', 'to'])
        deny = _phrase_in(u, ['nechci', 'ne'])

        for i, w in enumerate(u):
            if w.startswith("DATE_REL="):
                value = w[9:]

                if confirm:
                    cn.add(1.0, DialogueActItem("confirm", 'date_rel', value))
                elif deny:
                    cn.add(1.0, DialogueActItem("deny", 'date_rel', value))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'date_rel', value))

    def parse_ampm(self, abutterance, cn):
        """Detects the ampm in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance

        confirm = _phrase_in(u, ['jede', 'to'])
        deny = _phrase_in(u, ['nechci', 'ne'])

        for i, w in enumerate(u):
            if w.startswith("AMPM="):
                value = w[5:]

                if confirm:
                    cn.add(1.0, DialogueActItem("confirm", 'ampm', value))
                elif deny:
                    cn.add(1.0, DialogueActItem("deny", 'ampm', value))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'ampm', value))

    def parse_trans_type(self, abutterance, cn):
        """Detects the transport type in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance

        confirm = _phrase_in(u, ['jede', 'to'])
        deny = _phrase_in(u, ['nechci', 'jet'])

        for i, w in enumerate(u):
            if w.startswith("TRANS_TYPE="):
                value = w[11:]

                if confirm:
                    cn.add(1.0, DialogueActItem("confirm", 'trans_type', value))
                elif deny:
                    cn.add(1.0, DialogueActItem("deny", 'trans_type', value))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'trans_type', value))

    def parse_task(self, abutterance, cn):
        """Detects the task in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance

        deny = _phrase_in(u, ['nechci', 'nehledám'])

        for i, w in enumerate(u):
            if w.startswith("TASK="):
                value = w[5:]

                if deny:
                    cn.add(1.0, DialogueActItem("deny", 'task', value))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'task', value))

    def parse_meta(self, utterance, cn):
        """
        Detects all dialogue acts which do not generalise its slot values using CLDB.

        :param utterance:
        :param cn:
        :return: None
        """
        u = utterance
        if "_noise_" in u.utterance or len(u.utterance) == 0:
            cn.add(1.0, DialogueActItem("null"))

        if "_silence_" in u.utterance:
            cn.add(1.0, DialogueActItem("silence"))

        if "_other_" in u.utterance:
            cn.add(1.0, DialogueActItem("other"))

        if (_any_word_in(u, ["ahoj", "áhoj", "nazdar", "zdar",]) or
                _all_words_in(u, ["dobrý",  "den"])):
            cn.add(1.0, DialogueActItem("hello"))

        if (_any_word_in(u,["nashledanou", "shledanou", "shle", "nashle", "sbohem", "bohem", "zbohem", "zbohem", "konec",
                            "hledanou", "naschledanou"])):
            cn.add(1.0, DialogueActItem("bye"))

        if not _any_word_in(u, ["spojení", "zastávka", "stanice", "možnost"]):
            if _any_word_in(u, ["jiný", "jiné", "jiná", "jiného"]):
                cn.add(1.0, DialogueActItem("reqalts"))

        if not (_any_word_in(u,["spojení", "zastávka", "stanice", "možnost"])):
            if (_any_word_in(u,["zopakovat",  "opakovat", "znova", "znovu", "opakuj", "zopakuj"])
                    or _phrase_in(u, ["ještě", "jednou"])):
                cn.add(1.0, DialogueActItem("repeat"))

        if _any_word_in(u, ["nápověda",  "pomoc", "help", "nevím", "nevim"]) or \
            _all_words_in(u, ["co", "říct"]) or \
            _all_words_in(u, ["co", "zeptat"]):
            cn.add(1.0, DialogueActItem("help"))

        if _any_word_in(u, ["ano",  "jo", "jasně"]) and \
            not _any_word_in(u, ["nerozuměj",  ]) :
            cn.add(1.0, DialogueActItem("affirm"))

        if _any_word_in(u, ["ne", "nejedu"]):
            cn.add(1.0, DialogueActItem("negate"))

        if _any_word_in(u,["díky", "dikec", "děkuji", "děkuju", "děkují"]):
            cn.add(1.0, DialogueActItem("thankyou"))

        if _any_word_in(u,["ok", "pořádku",]):
            cn.add(1.0, DialogueActItem("ack"))

        if _any_word_in(u, ["od", "začít", ]) and _any_word_in(u, ["začátku", "znova", "znovu"]) or \
            _any_word_in(u, ["restart", ]) or \
           _phrase_in(u, ["nové", "spojení"]) and not _phrase_in(u, ["spojení", "ze", ]) or \
           _phrase_in(u, ["nový", "spoj"]) and not _phrase_in(u, ["spoj", "ze", ]):
            cn.add(1.0, DialogueActItem("restart"))

        if len(u.utterance) == 1 and _any_word_in(u, ["centra", "centrum", ]):
            # we do not know whether to or from and it must be one of them
            cn.add(1.0, DialogueActItem('inform','centre_direction','*'))

        if _phrase_in(u, ["z", "centra"]) and not _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('inform','centre_direction','from'))

        if _phrase_in(u, ["do", "centra"]) and not _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('inform','centre_direction','to'))

        if _phrase_in(u, ["z", "centra"]) and _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('deny','centre_direction','from'))

        if _phrase_in(u, ["do", "centra"]) and _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('deny','centre_direction','to'))

        if _all_words_in(u, ["od", "to", "jede"]) or \
            _all_words_in(u, ["z", "jake", "jede"]) or \
            _all_words_in(u, ["z", "jaké", "jede"]) or \
            _all_words_in(u, ["jaká", "výchozí", ]) or \
            _all_words_in(u, ["kde", "začátek", ]) or \
            _all_words_in(u, ["odkud", "to", "jede"]) or \
            _all_words_in(u, ["odkud", "jede"]) or \
            _all_words_in(u, ["odkud", "pojede"]) or \
            _all_words_in(u, ["od", "kud", "pojede"]):
            cn.add(1.0, DialogueActItem('request', 'from_stop'))

        if _all_words_in(u, ["kam", "to", "jede"]) or \
            _all_words_in(u, ["na", "jakou", "jede"]) or \
            _all_words_in(u, ["do", "jake", "jede"]) or \
            _all_words_in(u, ["do", "jaké", "jede"]) or \
            _all_words_in(u, ["co", "cíl", ]) or \
            _all_words_in(u, ["jaká", "cílová", ]) or \
            _all_words_in(u, ["kde", "konečná", ]) or \
            _all_words_in(u, ["kde", "konečná", ]) or \
            _all_words_in(u, ["kam", "pojede"]):
            cn.add(1.0, DialogueActItem('request', 'to_stop'))

        if _all_words_in(u, ['kdy', 'tam', 'budu']) or \
            (_all_words_in(u, ['kdy']) and
             _any_word_in(['příjezd', 'přijede', 'dorazí',
                           'přijedu', 'dorazím'])):
            cn.add(1.0, DialogueActItem('request', 'arrive_at'))

        if _all_words_in(u, ["kdy", "to", "jede"]) or \
            _all_words_in(u, ["kdy", "mi", "jede"]) or \
            _all_words_in(u, ["v", "kolik", "jede"]) or \
            _all_words_in(u, ["kdy", "to", "pojede"]):
            cn.add(1.0, DialogueActItem('request','time'))

        if _all_words_in(u, ["za", "jak", "dlouho", "jede"]) or \
            _all_words_in(u, ["za", "kolik", "minut", "jede"]) or \
            _all_words_in(u, ["za", "kolik", "minut", "pojede"]) or \
            _all_words_in(u, ["za", "jak", "dlouho", "pojede"]):
            cn.add(1.0, DialogueActItem('request','time_rel'))

        if _any_word_in(u, ["kolik", "jsou", "je"]) and \
            _any_word_in(u, ["přestupů", "přestupu", "přestupy", "stupňů", "přestup", "přestupku", "přestupky", "přestupků"]):
            cn.add(1.0, DialogueActItem('request','num_transfers'))

        if _any_word_in(u, ["spoj", "spojení", "spoje", "možnost", "možnosti", "cesta", "cestu", "cesty", "zpoždění", "stažení"]):
            if _any_word_in(u, ["první", ]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "1"))

            if _any_word_in(u, ["druhé", "druhá", "druhou"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "2"))

            if _any_word_in(u, ["třetí"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "3"))

            if _any_word_in(u, ["čtvrté", "čtvrtá", "čtvrtou"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "4"))

            if _any_word_in(u, ["poslední", "znovu", "znova", "opakovat", "zopakovat"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "last"))

            if _any_word_in(u, ["další", "jiné", "následující"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

            if _any_word_in(u, ["předchozí", "před"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if len(u) == 1 and _any_word_in(u, ["další", "následující"]):
            cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

        if len(u) == 1 and _any_word_in(u, ["předchozí", "před"]):
            cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if _any_word_in(u, ["neslyšíme", "halo", "haló"]) :
            cn.add(1.0, DialogueActItem('canthearyou'))

    def parse_1_best(self, obs, verbose=False):
        """Parse an utterance into a dialogue act."""
        utterance = obs['utt']

        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        if verbose:
            print 'Parsing utterance "{utt}".'.format(utt=utterance)

        if self.preprocessing:
            # the text normalisation
            utterance = self.preprocessing.normalise_utterance(utterance)

            abutterance, category_labels = self.preprocessing.values2category_labels_in_utterance(utterance)

            if verbose:
                print 'After preprocessing: "{utt}".'.format(utt=abutterance)
                print category_labels
        else:
            category_labels = dict()

        #print 'After preprocessing: "{utt}".'.format(utt=abutterance)
        #print category_labels
        #
        res_cn = DialogueActConfusionNetwork()

        if 'STOP' in category_labels:
            self.parse_stop(abutterance, res_cn)
        if 'TIME' in category_labels:
            self.parse_time(abutterance, res_cn)
        if 'TIME_REL' in category_labels:
            self.parse_time_rel(abutterance, res_cn)
        if 'DATE_REL' in category_labels:
            self.parse_date_rel(abutterance, res_cn)
        if 'AMPM' in category_labels:
            self.parse_ampm(abutterance, res_cn)
        if 'TRANS_TYPE' in category_labels:
            self.parse_trans_type(abutterance, res_cn)
        if 'TASK' in category_labels:
            self.parse_task(abutterance, res_cn)

        self.parse_meta(utterance, res_cn)

        return res_cn
