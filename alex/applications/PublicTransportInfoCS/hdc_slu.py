#!/usr/bin/env python
# encoding: utf8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

from alex.components.asr.utterance import Utterance, UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork

# if there is a change in search parameters from_stop, to_stop, time, then
# reset alternatives

def _any_word_in(utterance, words):
    words = words if not isinstance(words, basestring) else words.strip().split()
    for alt_expr in words:
        if  alt_expr in utterance.utterance:
            return True

    return False


def _all_words_in(utterance, words):
    words = words if not isinstance(words, basestring) else words.strip().split()
    for alt_expr in words:
        if  alt_expr not in utterance.utterance:
            return False
    return True


def _phrase_in(utterance, words):
    utterance = utterance if not isinstance(utterance, list) else Utterance(' '.join(utterance))
    words = words if not isinstance(words, basestring) else words.strip().split()
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
        preps_from = set(["z", "za", "ze", "od", "začátek", "začáteční", "počáteční", "počátek", "výchozí", "start"])
        preps_to = set(["k", "do", "konec", "na", "konečná", "koncová", "cílová", "cíl", "výstupní"])
        preps_via = set(["přes", ])

        fillers_from = set(["start", "stojím", "jsem" ])
        fillers_to = set(["cíl", ])
        fillers_via = set([])

        u = abutterance
        N = len(u)

        confirm = lambda u: _phrase_in(u, 'jede to') or _phrase_in(u, 'odjíždí to') or _phrase_in(u, 'je výchozí')
        deny = lambda u: _phrase_in(u, 'nechci jet') or _phrase_in(u, 'nechci odjíždět') or _phrase_in(u, 'nejedu')


        last_stop = 0
        for i, w in enumerate(u):
            if w.startswith("STOP="):
                stop_name = w[5:]
                from_stop = False
                to_stop = False
                via_stop = False
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
                        elif u[i - 3] in preps_from:
                            from_stop = True
                            stop_decided = True
                        elif u[i - 3] in preps_to:
                            to_stop = True
                            stop_decided = True
                        elif u[i - 3] in preps_via:
                            via_stop = True
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
                        elif u[i - 2] in preps_via:
                            via_stop = True
                            stop_decided = True

                if not stop_decided and i >= 1:
                    if u[i - 1] in preps_from:
                        from_stop = True
                        stop_decided = True
                    elif u[i - 1] in preps_to:
                        to_stop = True
                        stop_decided = True
                    elif u[i - 1] in preps_via:
                        via_stop = True
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

                if confirm(u[last_stop:i]):
                    dat = "confirm"
                elif deny(u[last_stop:i]):
                    dat = "deny"
                else:
                    dat = "inform"

                if from_stop and not to_stop and not via_stop:
                    cn.add(1.0, DialogueActItem(dat, "from_stop", stop_name))

                if not from_stop and to_stop and not via_stop:
                    cn.add(1.0, DialogueActItem(dat, "to_stop", stop_name))

                if not from_stop and not to_stop and via_stop:
                    cn.add(1.0, DialogueActItem(dat, "via_stop", stop_name))

                # backoff 1: add both from and to stop slots
                if from_stop and to_stop:
                    cn.add(0.501, DialogueActItem(dat, "from_stop", stop_name))
                    cn.add(0.499, DialogueActItem(dat, "to_stop", stop_name))

                # backoff 2: we do not know what slot it belongs to, let the DM
                # decide in the context resolution
                if ((not from_stop and not to_stop and not via_stop) or \
                        (from_stop and to_stop)):
                    cn.add(0.501, DialogueActItem(dat, "", stop_name))
                    cn.add(0.499, DialogueActItem(dat, "", stop_name))

                last_stop = i

    def parse_time(self, abutterance, cn):
        """Detects the time in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance
        N = len(u)

        preps_abs = set(["v", "ve", "čas", "o", "po", "před", "kolem"])
        preps_rel = set(["za", ])

        confirm = lambda u: _phrase_in(u, 'jede to') or _phrase_in(u, 'odjíždí to') or _phrase_in(u, 'je výchozí')
        deny = lambda u: _phrase_in(u, 'nechci jet') or _phrase_in(u, 'nechci odjíždět') or _phrase_in(u, 'nejedu')

        last_time = 0
        for i, w in enumerate(u):
            if w.startswith("TIME="):
                value = w[5:]
                time_abs = False
                time_rel = False

                if i >= 1:
                    if u[i - 1] in preps_abs:
                        time_abs = True
                    if u[i - 1] in preps_rel:
                        time_rel = True

                if value == "now" and \
                    not _phrase_in(u, 'no a') and \
                    not _phrase_in(u, 'kolik je') and \
                    not _phrase_in(u, 'neslyším') and \
                    not _phrase_in(u, 'už mi neříká'):
                    time_rel = True

                if confirm(u[last_time:i]):
                    dat = "confirm"
                elif deny(u[last_time:i]):
                    dat = "deny"
                else:
                    dat = "inform"

                if time_abs:
                    cn.add(1.0, DialogueActItem(dat, 'departure_time', value))
                elif time_rel:
                    cn.add(1.0, DialogueActItem(dat, 'departure_time_rel', value))

                last_time = i

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

                if value == "now" and not _phrase_in(u, 'no a') and \
                        not _phrase_in(u, 'kolik je') and \
                        not _phrase_in(u, 'neslyším') and \
                        not _phrase_in(u, 'už mi neříká'):
                    time = True

                if confirm:
                    dat = "confirm"
                elif deny:
                    dat = "deny"
                else:
                    dat = "inform"

                if time:
                    cn.add(1.0, DialogueActItem(dat, 'departure_time_rel', value))

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

                if not (_phrase_in(u, 'dobrou')):
                    if confirm:
                        cn.add(1.0, DialogueActItem("confirm", 'ampm', value))
                    elif deny:
                        cn.add(1.0, DialogueActItem("deny", 'ampm', value))
                    else:
                        cn.add(1.0, DialogueActItem("inform", 'ampm', value))

    def parse_vehicle(self, abutterance, cn):
        """Detects the vehicle (transport type) in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance

        confirm = _phrase_in(u, ['jede', 'to'])
        deny = _phrase_in(u, ['nechci', 'jet'])

        for i, w in enumerate(u):
            if w.startswith("VEHICLE="):
                value = w[8:]

                if confirm:
                    cn.add(1.0, DialogueActItem("confirm", 'vehicle', value))
                elif deny:
                    cn.add(1.0, DialogueActItem("deny", 'vehicle', value))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'vehicle', value))

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
        if "_noise_" in u.utterance or "_laugh_" in u.utterance or "_inhale_" in u.utterance or len(u.utterance) == 0:
            cn.add(1.0, DialogueActItem("null"))

        if "_silence_" in u.utterance or "__silence__" in u.utterance or "_sil_" in u.utterance:
            cn.add(1.0, DialogueActItem("silence"))

        if "_other_" in u.utterance or "__other__" in u.utterance or "_ehm_hmm_" in u.utterance:
            cn.add(1.0, DialogueActItem("other"))

        if (_any_word_in(u, ["ahoj", "áhoj", "nazdar", "zdar", ]) or
                _all_words_in(u, ["dobrý", "den"])):
            cn.add(1.0, DialogueActItem("hello"))

        if (_any_word_in(u, "nashledanou shledanou schledanou shle nashle sbohem bohem zbohem zbohem konec hledanou "
                            "naschledanou čau čauky čaues")):
            cn.add(1.0, DialogueActItem("bye"))

        if not _any_word_in(u, ["spojení", "zastávka", "stanice", "možnost", "varianta"]):
            if _any_word_in(u, ["jiný", "jiné", "jiná", "jiného"]):
                cn.add(1.0, DialogueActItem("reqalts"))

        if not _any_word_in(u, ["spojení", "zastávka", "stanice", "možnost", "spoj", "nabídnutý", "poslední", "nalezená", "začátku"]):
            if (_any_word_in(u, ["zopakovat", "opakovat", "znova", "znovu", "opakuj", "zopakuj", 'zopakujte']) or
                _phrase_in(u, "ještě jednou")):
                cn.add(1.0, DialogueActItem("repeat"))

        if _phrase_in(u, "zopakuj poslední větu"):
            cn.add(1.0, DialogueActItem("repeat"))

        if len(u) == 1 and _any_word_in(u, "pardon pardón promiňte"):
            cn.add(1.0, DialogueActItem("apology"))

        if not _any_word_in(u, "nechci"):
            if _any_word_in(u, "nápověda nápovědu pomoc pomoct pomoci pomož pomohla pomohl pomůžete help nevím nevim") or \
                _all_words_in(u, ["co", "říct"]) or \
                _all_words_in(u, ["co", "zeptat"]):
                cn.add(1.0, DialogueActItem("help"))

        if _any_word_in(u, "ano jo jasně") and \
            not _any_word_in(u, "nerozuměj nechci vzdávám čau možnost konec") :
            cn.add(1.0, DialogueActItem("affirm"))

        if _any_word_in(u, "ne né") or \
            len(u) == 1 and _any_word_in(u, "nejedu nechci") or \
            len(u) == 2 and _all_words_in(u, "ano nechci") or \
            _all_words_in(u, "to je špatně"):
            cn.add(1.0, DialogueActItem("negate"))

        if _any_word_in(u, ["díky", "dikec", "děkuji", "dekuji", "děkuju", "děkují"]):
            cn.add(1.0, DialogueActItem("thankyou"))

        if _any_word_in(u, ["ok", "pořádku", "dobře", "správně"]) and \
            not _any_word_in(u, "ano"):
            cn.add(1.0, DialogueActItem("ack"))

        if _any_word_in(u, "od začít") and _any_word_in(u, "začátku znova znovu") or \
            _any_word_in(u, "reset resetuj restart restartuj") or \
            _phrase_in(u, ["nové", "spojení"]) and not _phrase_in(u, ["spojení", "ze", ]) or \
            _phrase_in(u, ["nový", "spojení"]) and not _phrase_in(u, ["spojení", "ze", ]) or \
            _phrase_in(u, ["nové", "zadání"]) and not _any_word_in(u, "ze") or \
            _phrase_in(u, ["nový", "zadání"]) and not _any_word_in(u, "ze") or \
            _phrase_in(u, ["nový", "spoj"]) and not _phrase_in(u, "spoj ze"):
            cn.add(1.0, DialogueActItem("restart"))

        if len(u.utterance) == 1 and _any_word_in(u, ["centra", "centrum", ]):
            # we do not know whether to or from and it must be one of them
            cn.add(1.0, DialogueActItem('inform', 'centre_direction', '*'))

        if _phrase_in(u, ["z", "centra"]) and not _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('inform', 'centre_direction', 'from'))

        if _phrase_in(u, ["do", "centra"]) and not _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('inform', 'centre_direction', 'to'))

        if _phrase_in(u, ["z", "centra"]) and _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('deny', 'centre_direction', 'from'))

        if _phrase_in(u, ["do", "centra"]) and _any_word_in(u, ["ne", "nejedu", "nechci"]):
            cn.add(1.0, DialogueActItem('deny', 'centre_direction', 'to'))

        if _all_words_in(u, ["od", "to", "jede"]) or \
            _all_words_in(u, ["z", "jake", "jede"]) or \
            _all_words_in(u, ["z", "jaké", "jede"]) or \
            _all_words_in(u, ["z", "jaké", "zastávky"]) or \
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
            _all_words_in(u, ["do", "jaké", "zastávky"]) or \
            _all_words_in(u, ["co", "cíl", ]) or \
            _all_words_in(u, ["jaká", "cílová", ]) or \
            _all_words_in(u, ["kde", "konečná", ]) or \
            _all_words_in(u, ["kde", "konečná", ]) or \
            _all_words_in(u, "kam jede") or \
            _all_words_in(u, "kam pojede"):
            cn.add(1.0, DialogueActItem('request', 'to_stop'))

        if not _any_word_in(u, 'za budu bude budem přijede přijedete přijedu dojedu dorazí dorazím dorazíte'):
            if _all_words_in(u, "kdy jede") or \
                _all_words_in(u, "v kolik jede") or \
                _all_words_in(u, "v kolik hodin") or \
                _all_words_in(u, "kdy to pojede") or \
                (_any_word_in(u, 'kdy kolik') and  _any_word_in(u, 'jede odjíždí odjede odjíždíš odjíždíte')):
                cn.add(1.0, DialogueActItem('request', 'departure_time'))

        if not _any_word_in(u, 'budu bude budem přijede přijedete přijedu dojedu dorazí dorazím dorazíte'):
            if _all_words_in(u, "za jak dlouho") or \
                _all_words_in(u, "za kolik minut jede") or \
                _all_words_in(u, "za kolik minut pojede") or \
                _all_words_in(u, "za jak dlouho pojede"):
                cn.add(1.0, DialogueActItem('request', 'departure_time_rel'))

        if (_all_words_in(u, 'kdy tam') and _any_word_in(u, 'budu bude budem')) or \
            (_all_words_in(u, 'v kolik tam') and _any_word_in(u, 'budu bude budem')) or \
            (_all_words_in(u, 'v kolik hodin') and _any_word_in(u, 'budu bude budem')) or \
            _all_words_in(u, 'čas příjezdu') or \
            (_any_word_in(u, 'kdy kolik') and  _any_word_in(u, 'příjezd přijede přijedete přijedu přijedem dojedu dorazí dorazím dorazíte')):
            cn.add(1.0, DialogueActItem('request', 'arrival_time'))

        if _all_words_in(u, 'za jak dlouho tam') and _any_word_in(u, "budu bude budem přijedu přijede přijedem přijedete dojedu dorazí dorazím dorazíte"):
            cn.add(1.0, DialogueActItem('request', 'arrival_time_rel'))

        if not _any_word_in(u, 'za'):
            if _all_words_in(u, 'jak dlouho') and _any_word_in(u, "jede pojede trvá trvat"):
                cn.add(1.0, DialogueActItem('request', 'duration'))

        if _all_words_in(u, 'kolik je hodin'):
            cn.add(1.0, DialogueActItem('request', 'current_time'))

        if _any_word_in(u, ["kolik", "jsou", "je"]) and \
            _any_word_in(u, ["přestupů", "přestupu", "přestupy", "stupňů", "přestup", "přestupku", "přestupky", "přestupků"]):
            cn.add(1.0, DialogueActItem('request', 'num_transfers'))

        if _any_word_in(u, ["spoj", "spojení", "spoje", "možnost", "možnosti", "varianta", 'alternativa', "cesta", "cestu", "cesty",
                            "zpoždění", "stažení", "nalezená"]):
            if _any_word_in(u, ["první", "jedna"]) and \
                not _any_word_in(u, 'druhá druhý třetí čtvrtá čtvrtý'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "1"))

            if _any_word_in(u, ["druhé", "druhá", "druhou", "dva"])and \
                not _any_word_in(u, 'třetí čtvrtá čtvrtý další'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "2"))

            if _any_word_in(u, ["třetí", "tři"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "3"))

            if _any_word_in(u, ["čtvrté", "čtvrtá", "čtvrtou", "čtyři"]):
                cn.add(1.0, DialogueActItem("inform", "alternative", "4"))

            if _any_word_in(u, "poslední znovu znova opakovat zopakovat zopakujte") and \
                not _all_words_in(u, "předchozí"):
                cn.add(1.0, DialogueActItem("inform", "alternative", "last"))

            if _any_word_in(u, "další jiné jiná následující") or \
                _phrase_in(u, "ještě jedno") or \
                _phrase_in(u, "ještě jednu"):
                cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

            if _any_word_in(u, "předchozí před"):
                if _phrase_in(u, "nechci vědět předchozí"):
                    cn.add(1.0, DialogueActItem("deny", "alternative", "prev"))
                else:
                    cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if len(u) == 1 and _any_word_in(u, 'další následující následují'):
            cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

        if len(u) == 2 and \
            (_all_words_in(u, "a další") or  _all_words_in(u, "a později")):
            cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

        if len(u) == 1 and _any_word_in(u, "předchozí před"):
            cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if _any_word_in(u, "neslyšíme neslyším halo haló") :
            cn.add(1.0, DialogueActItem('canthearyou'))

        if _all_words_in(u, "nerozuměl jsem") or \
            _all_words_in(u, "nerozuměla jsem") or \
            _all_words_in(u, "taky nerozumím") or \
            _all_words_in(u, "nerozumím vám") or \
            (len(u) == 1 and _any_word_in(u, "nerozumím")):
            cn.add(1.0, DialogueActItem('notunderstood'))

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
        if 'DATE_REL' in category_labels:
            self.parse_date_rel(abutterance, res_cn)
        if 'AMPM' in category_labels:
            self.parse_ampm(abutterance, res_cn)
        if 'VEHICLE' in category_labels:
            self.parse_vehicle(abutterance, res_cn)
        if 'TASK' in category_labels:
            self.parse_task(abutterance, res_cn)

        self.parse_meta(utterance, res_cn)

        res_cn.merge()

        return res_cn
