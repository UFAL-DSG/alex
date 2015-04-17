#!/usr/bin/env python
# encoding: utf8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import copy
import codecs
from ast import literal_eval
from itertools import chain

from alex.components.asr.utterance import Utterance, UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork, DialogueAct

# if there is a change in search parameters from_stop, to_stop, time, then
# reset alternatives


def any_word_in(utterance, words):
    words = words if not isinstance(words, basestring) else words.strip().split()
    for alt_expr in words:
        if alt_expr in utterance.utterance:
            return True
    return False


def all_words_in(utterance, words):
    words = words if not isinstance(words, basestring) else words.strip().split()
    for alt_expr in words:
        if alt_expr not in utterance.utterance:
            return False
    return True


def phrase_in(utterance, words):
    return phrase_pos(utterance, words) != -1


def phrase_pos(utterance, words):
    """Returns the position of the given phrase in the given utterance, or -1 if not found.

    :rtype: int
    """
    utterance = utterance if not isinstance(utterance, list) else Utterance(' '.join(utterance))
    words = words if not isinstance(words, basestring) else words.strip().split()
    return utterance.find(words)


def first_phrase_span(utterance, phrases):
    """Returns the span (start, end+1) of the first phrase from the given list
    that is found in the utterance. Returns (-1, -1) if no phrase is found.

    :param utterance: The utterance to search in
    :param phrases: a list of phrases to be tried (in the given order)
    :rtype: tuple
    """
    for phrase in phrases:
        pos = phrase_pos(utterance, phrase)
        if pos != -1:
            return pos, pos + len(phrase.split())
    return -1, -1


def any_phrase_in(utterance, phrases):
    return first_phrase_span(utterance, phrases) != (-1, -1)


def ending_phrases_in(utterance, phrases):
    """Returns True if the utterance ends with one of the phrases

    :param utterance: The utterance to search in
    :param phrases: a list of phrases to search for
    :rtype: bool
    """

    utterance = utterance if not isinstance(utterance, list) else Utterance(' '.join(utterance))
    utterance_len = len(utterance)

    for phrase in phrases:
        phr_pos = phrase_pos(utterance, phrase)
        if phr_pos is not -1 and phr_pos + len(phrase.split()) is utterance_len:
            return True
    return False


class DAIBuilder(object):
    """
    Builds DialogueActItems with proper alignment to corresponding utterance words.
    When words are successfully matched using DAIBuilder, their indices in the utterance are
    added to alignment set of the DAI as a side-effect.
    """

    def __init__(self, utterance, abutterance_lenghts=None):
        """
        :param utterance: utterance to search words in
        :type utterance: Utterance
        :param abutterance_lenghts: numbers of utterance words that correspond to each abutterance word.
            I.e.: an element is 1 if respective abutterance word is unabstracted utterance words
        :type abutterance_lenghts: list[int]
        """
        self._utterance = utterance if not isinstance(self, list) else Utterance(' '.join(utterance))
        self.utt2abutt_idxs = range(len(utterance)) if not abutterance_lenghts else \
            list(chain.from_iterable([idx]*abutterance_lenghts[idx] for idx in range(len(abutterance_lenghts))))
        self._alignment = set()

    def build(self, act_type=None, slot=None, value=None):
        """
        Produce DialogueActItem based on arguments and alignment from this DAIBuilder state.
        """
        dai = DialogueActItem(act_type, slot, value, alignment={self.utt2abutt_idxs[i] for i in self._alignment})
        self.clear()
        return dai

    def clear(self):
        self._alignment = set()

    def _words_in(self, qualifier, words):
        words = words if not isinstance(words, basestring) else words.strip().split()
        if qualifier(word in self._utterance.utterance for word in words):
            indices = [i for i, word in enumerate(self._utterance.utterance) if word in words]
            self._alignment.update(indices)
            return True
        else:
            return False

    def any_word_in(self, words):
        return self._words_in(any, words)

    def all_words_in(self, words):
        return self._words_in(all, words)

    def phrase_pos(self, words, sub_utt=None):
        """Returns the position of the given phrase in the given utterance, or -1 if not found.

        :rtype: int
        """
        utt = Utterance(self._utterance[sub_utt[0]:sub_utt[1]]) if sub_utt else self._utterance
        words = words if not isinstance(words, basestring) else words.strip().split()
        return utt.find(words)

    def first_phrase_span(self, phrases, sub_utt=None):
        """Returns the span (start, end+1) of the first phrase from the given list
        that is found in the utterance. Returns (-1, -1) if no phrase is found.

        :param phrases: a list of phrases to be tried (in the given order)
        :rtype: tuple
        """
        for phrase in phrases:
            pos = self.phrase_pos(phrase, sub_utt)
            if pos != -1:
                self._alignment.update(range(pos, pos+len(phrase.split())))
                return pos, pos+len(phrase)
        return -1, -1

    def any_phrase_in(self, phrases, sub_utt=None):
        return self.first_phrase_span(phrases, sub_utt) != (-1, -1)

    def phrase_in(self, phrase, sub_utt=None):
        return self.any_phrase_in([phrase], sub_utt)

    def ending_phrases_in(self, phrases):
        """Returns True if the utterance ends with one of the phrases

        :param phrases: a list of phrases to search for
        :rtype: bool
        """
        utterance = self._utterance if not isinstance(self, list) else Utterance(' '.join(self._utterance))
        for phrase in phrases:
            pos = self.phrase_pos(phrase)
            if pos is not -1 and pos + len(phrase.split()) is len(utterance):
                self._alignment.update(range(pos, pos+len(phrase.split())))
                return True
        return False


class PTICSHDCSLU(SLUInterface):

    def __init__(self, preprocessing, cfg):
        super(PTICSHDCSLU, self).__init__(preprocessing, cfg)
        self.cldb = self.preprocessing.cldb
        if 'utt2da' in cfg['SLU'][PTICSHDCSLU]:
            self.utt2da = self._load_utt2da(cfg['SLU'][PTICSHDCSLU]['utt2da'])
        else:
            self.utt2da = {}

    def _load_utt2da(self, filename):
        """
        Load a dictionary mapping utterances directly to dialogue acts for the utterances
        that are either too complicated or too unique to be parsed by HDC SLU rules.

        :param filename: path to file with a list of utterances transcriptions and corresponding dialogue acts
        :return: a dictionary from utterance to dialogue act
        :rtype: dict
        """
        utt2da = {}
        with codecs.open(filename, 'r', 'UTF-8') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.split('\t')
                    utt2da[unicode(key)] = val
        return utt2da

    def abstract_utterance(self, utterance):
        """
        Return a list of possible abstractions of the utterance.

        :param utterance: an Utterance instance
        :return: a list of abstracted utterance, form, value, category label tuples
        """
        abs_utts = copy.deepcopy(utterance)
        category_labels = set()
        abs_utt_lengths = [1] * len(abs_utts)
        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end > start:
                f = tuple(utterance[start:end])
                # print start, end
                # print f

                if f in self.cldb.form2value2cl:
                    for v in self.cldb.form2value2cl[f]:
                        for c in self.cldb.form2value2cl[f][v]:
                            abs_utts = abs_utts.replace(f, (c.upper() + '='+v,))
                            abs_utt_lengths[start] = len(f)
                            category_labels.add(c.upper())
                            break
                        else:
                            continue

                        break

                    # print f

                    # skip all substring for this form
                    start = end
                    break
                end -= 1
            else:
                start += 1
        # normalize abstract utterance lengths
        norm_abs_utt_lengths = []
        i = 0
        while i < len(abs_utt_lengths):
            l = abs_utt_lengths[i]
            norm_abs_utt_lengths.append(l)
            i += l
        return abs_utts, category_labels, norm_abs_utt_lengths


    def __repr__(self):
        return "PTICSHDCSLU({preprocessing}, {cfg})".format(preprocessing=self.preprocessing, cfg=self.cfg)

    def parse_stop(self, abutterance, cn):
        """ Detects stops in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        # regular parsing
        phr_wp_types = [('from', set(['z', 'za', 'ze', 'od', 'začátek', 'začáteční',
                                      'počáteční', 'počátek', 'výchozí', 'start', 'stojím na',
                                      'jsem na', 'start na', 'stojím u', 'jsem u', 'start u',
                                      'začátek na', 'začátek u'])),
                        ('to', set(['k', 'do', 'konec', 'na', 'konečná', 'koncová',
                                    'cílová', 'cíl', 'výstupní', 'cíl na', 'chci na'])),
                        ('via', set(['přes', ]))]

        self.parse_waypoint(abutterance, cn, 'STOP=', 'stop', phr_wp_types)

    def parse_city(self, abutterance, cn):
        """ Detects stops in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        # regular parsing
        phr_wp_types = [('from', set(['z', 'ze', 'od', 'začátek', 'začáteční',
                                      'počáteční', 'počátek', 'výchozí', 'start',
                                      'jsem v', 'stojím v', 'začátek v'])),
                        ('to', set(['k', 'do', 'konec', 'na', 'končím',
                                    'cíl', 'vystupuji', 'vystupuju'])),
                        ('via', set(['přes', ])),
                        ('in', set(['pro', 'po'])),
                       ]

        self.parse_waypoint(abutterance, cn, 'CITY=', 'city', phr_wp_types, phr_in=['v', 've'])

    def parse_waypoint(self, abutterance, cn, wp_id, wp_slot_suffix, phr_wp_types, phr_in=None):
        """Detects stops or cities in the input abstract utterance
        (called through parse_city or parse_stop).

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        :param wp_id: waypoint slot category label (e.g. "STOP=", "CITY=")
        :param wp_slot_suffix: waypoint slot suffix (e.g. "stop", "city")
        :param phr_wp_types: set of phrases for each waypoint type
        :param phr_in: phrases for 'in' waypoint type
        """
        u = abutterance
        N = len(u)

        # simple "ne" cannot be included as it collides with negation. "ne [,] chci jet z Motola"
        phr_dai_types = [('confirm', set(['jede to', 'odjíždí to', 'je výchozí']), set()),
                         ('deny',
                          # positive matches
                          set(['nechci', 'nejedu', 'ne z', 'ne od', 'ne na', 'ne do', 'né do', 'ne k', 'nikoliv', 'nechci na', 'nechtěl']),
                          # negative matches
                          set(['nechci ukončit hovor', 'nechci to tak', 'né to nechci', 'ne to nechci', 'nechci nápovědu',
                               'nechci chci', 'ne to ne', 'ne ne z']))]
        last_wp_pos = 0

        for i, w in enumerate(u):
            if w.startswith(wp_id):
                wp_name = w[len(wp_id):]
                wp_types = set()
                dai_type = 'inform'

                # test short preceding context to find the stop type (from, to, via)
                wp_precontext = {}
                for cur_wp_type, phrases in phr_wp_types:
                    wp_precontext[cur_wp_type] = first_phrase_span(u[max(last_wp_pos, i - 5):i], phrases)
                wp_types |= self._get_closest_wp_type(wp_precontext)
                # test short following context (0 = from, 1 = to, 2 = via)
                if not wp_types:
                    if any_phrase_in(u[i:i + 3], phr_wp_types[0][1] | phr_wp_types[2][1]):
                        wp_types.add('to')
                    elif any_phrase_in(u[i:i + 3], phr_wp_types[1][1]):
                        wp_types.add('from')
                # resolve context according to further preceding/following waypoint name (assuming from-to)
                if not wp_types:
                    if i >= 1 and u[i - 1].startswith(wp_id):
                        wp_types.add('to')
                    elif i <= N - 2 and u[i + 1].startswith(wp_id):
                        wp_types.add('from')
                # using 'in' slot if the previous checks did not work and we have phrases for 'in'
                if not wp_types and phr_in is not None and any_phrase_in(u[max(last_wp_pos, i - 5): i], phr_in):
                    wp_types.add('in')

                # test utterance type
                for cur_dai_type, phrases_pos, phrases_neg in phr_dai_types:
                    if any_phrase_in(u[last_wp_pos:i], phrases_pos) and not any_phrase_in(u[last_wp_pos:i], phrases_neg):
                        dai_type = cur_dai_type
                        break

                # add waypoint to confusion network (standard case: just single type is decided)
                if len(wp_types) == 1:
                    cn.add(1.0, DialogueActItem(dai_type, wp_types.pop() + '_' + wp_slot_suffix, wp_name, alignment={i}))
                # backoff 1: add both 'from' and 'to' waypoint slots
                elif 'from' in wp_types and 'to' in wp_types:
                    cn.add(0.501, DialogueActItem(dai_type, 'from_' + wp_slot_suffix, wp_name, alignment={i}))
                    cn.add(0.499, DialogueActItem(dai_type, 'to_' + wp_slot_suffix, wp_name, alignment={i}))
                # backoff 2: let the DM decide in context resolution
                else:
                    cn.add(1.0, DialogueActItem(dai_type, wp_slot_suffix, wp_name, alignment={i}))

                last_wp_pos = i + 1

    def _get_closest_wp_type(self, wp_precontext):
        """Finds the waypoint type that goes last in the context (if same end points are
        encountered, the type with a longer span wins).

        :param wp_precontext: Dictionary waypoint type -> span (start, end+1) in the preceding \
            context of the waypoint mention
        :returns: one-member set with the best type (if there is one with non-negative position), \
            or empty set on failure
        :rtype: set
        """
        best_type = None
        best_pos = (-2, -1)
        for cur_type, cur_pos in wp_precontext.iteritems():
            if cur_pos[1] > best_pos[1] or cur_pos[1] == best_pos[1] and cur_pos[0] < best_pos[0]:
                best_type = cur_type
                best_pos = cur_pos
        if best_type is not None:
            return set([best_type])
        return set()

    def parse_number(self, abutterance):
        """Detect a number in the input abstract utterance

        Number words that form time expression are collapsed into a single TIME category word.
        Recognized time expressions (where FRAC, HOUR and MIN stands for fraction, hour and minute numbers respectively):
            - FRAC [na] HOUR
            - FRAC hodin*
            - HOUR a FRAC hodin*
            - HOUR hodin* a MIN minut*
            - HOUR hodin* MIN
            - HOUR hodin*
            - HOUR [0]MIN
            - MIN minut*

        Words of NUMBER category are assumed to be in format parsable to int or float

        :param abutterance: the input abstract utterance.
        :type abutterance: Utterance
        """
        def parse_number(word):
            return literal_eval(word[len("NUMBER="):])

        def hour_number(word):
            if not word.startswith("NUMBER="):
                return False
            num = parse_number(word)
            return isinstance(num, int) and 0 <= num < 24

        def minute_number(word):
            if not word.startswith("NUMBER="):
                return False
            num = parse_number(word)
            return isinstance(num, int) and 0 <= num < 60

        def fraction_number(word):
            if not word.startswith("NUMBER="):
                return False
            num = parse_number(word)
            return isinstance(num, float)

        u = abutterance
        i = 0
        while i < len(u):
            if fraction_number(u[i]):
                minute_num = int(parse_number(u[i]) * 60)
                # FRAC na HOUR
                if i < len(u)-2 and minute_num in [15, 45] and u[i+1] == 'na' and hour_number(u[i+2]):
                    u[i:i+3] = ["TIME_{len}={hour}:{min}".format(len=3, hour=parse_number(u[i+2])-1, min=minute_num)]
                # FRAC HOUR
                if i < len(u)-1 and minute_num == 30 and hour_number(u[i+1]):
                    u[i:i+2] = ["TIME_{len}={hour}:{min}".format(len=2, hour=parse_number(u[i+1])-1, min=minute_num)]
                # FRAC hodin*
                elif i < len(u)-1 and u[i+1].startswith('hodin'):
                    u[i:i+2] = ["TIME_{len}=0:{min}".format(len=2, min=minute_num)]
            elif hour_number(u[i]):
                hour_num = parse_number(u[i])
                # HOUR a FRAC hodin*
                if i < len(u)-3 and u[i+1] == 'a' and fraction_number(u[i+2]) and u[i+3].startswith('hodin'):
                    u[i:i+4] = ["TIME_{len}={hour}:{min}".format(len=4, hour=hour_num, min=int(parse_number(u[i+2]) * 60))]
                if i < len(u)-1 and u[i+1].startswith('hodin'):
                    # HOUR hodin* a MIN minut*
                    if i < len(u)-4 and u[i+2] == 'a' and minute_number(u[i+3]) and u[i+4].startswith('minut'):
                        u[i:i+5] = ["TIME_{len}={hour}:{min:0>2d}".format(len=5, hour=hour_num, min=parse_number(u[i+3]))]
                    # HOUR hodin* MIN
                    elif i < len(u)-3 and minute_number(u[i+2]):
                        u[i:i+4] = ["TIME_{len}={hour}:{min:0>2d}".format(len=4, hour=hour_num, min=parse_number(u[i+2]))]
                    # HOUR hodin*
                    else:
                        u[i:i+2] = ["TIME_{len}={hour}:00".format(len=2, hour=hour_num)]
                if i < len(u)-1 and minute_number(u[i+1]):
                    minute_num = parse_number(u[i+1])
                    # HOUR MIN
                    if minute_num > 9:
                        u[i:i+2] = ["TIME_{len}={hour}:{min}".format(len=2, hour=hour_num, min=minute_num)]
                    # HOUR 0 MIN (single digit MIN)
                    elif minute_num == 0 and i < len(u)-2 and minute_number(u[i+2]) and parse_number(u[i+2]) <= 9:
                        u[i:i+3] = ["TIME_{len}={hour}:{min:0>2d}".format(len=3, hour=hour_num, min=parse_number(u[i+2]))]
            if minute_number(u[i]):
                # MIN minut*
                if i < len(u)-1 and u[i+1].startswith("minut"):
                    u[i:i+2] = ["TIME_{len}=0:{min:0>2d}".format(len=2, min=parse_number(u[i]))]

            if i > 0:
                # v HOUR
                if u[i-1] == 'v' and hour_number(u[i]):
                    u[i] = "TIME_{len}={hour}:00".format(len=1, hour=parse_number(u[i]))
                # za hodinu/minutu
                elif u[i-1] == 'za':
                    if u[i] == 'hodinu':
                        u[i] = "TIME_1=1:00"
                    elif u[i] == 'minutu':
                        u[i] = "TIME_1=0:01"
            i += 1

    def parse_time(self, abutterance, cn):
        """Detects the time in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        u = abutterance

        # preps_abs = set(["v", "ve", "čas", "o", "po", "před", "kolem"])
        preps_rel = set(["za", ])

        test_context = [('confirm', 'departure',
                         ['jede to', 'odjíždí to', 'je výchozí', 'má to odjezd', 'je odjezd'],
                         []),
                        ('confirm', 'arrival',
                         ['přijede to', 'přijíždí to', 'má to příjezd', 'je příjezd'],
                         []),
                        ('confirm', '',
                         ['je to', 'myslíte', 'myslíš'],
                         []),
                        ('deny', 'departure',
                         ['nechci jet', 'nejedu', 'nechci odjíždět', 'nechci odjezd', 'nechci vyjet', 'nechci vyjíždět',
                         'nechci vyrážet', 'nechci vyrazit'],
                         []),
                        ('deny', 'arrival',
                         ['nechci přijet', 'nechci přijíždět', 'nechci příjezd', 'nechci dorazit'],
                         []),
                        ('deny', '',
                         ['ne', 'nechci'],
                         []),
                        ('inform', 'departure',
                         ['TASK=find_connection', 'odjezd', 'odjíždet', 'odjíždět', 'odjíždět v', 'odjíždí', 'odjet',
                         'jedu', 'jede', 'vyrážím', 'vyrážet', 'vyrazit', 'bych jel', 'bych jela', 'bych jet',
                         'bych tam jel', 'bych tam jela', 'bych tam jet',
                         'abych jel', 'abych jela', 'jak se dostanu', 'kdy jede', 'jede nějaká',
                         'jede nějaký', 'VEHICLE=tram', 'chci jet', 'chtěl jet', 'chtěla jet'],
                         ['příjezd', 'přijet', 'dorazit', 'abych přijel', 'abych přijela', 'chci být', 'chtěl bych být']),
                        ('inform', 'arrival',
                         ['příjezd', 'přijet', 'dorazit', 'abych přijel', 'abych přijela', 'chci být', 'chtěl bych být'],
                         []),
                        ('inform', '',
                         [],
                         []),
        ]

        count_times = 0
        for i, w in enumerate(u):
            if w.startswith("TIME_") or w.startswith("TIME="):
                count_times += 1

        last_time_type = ''
        last_time = 0

        for i, w in enumerate(u):
            if w.startswith("TIME_") or w.startswith("TIME="):
                if w.startswith("TIME_"):
                    num_len = int(w[5])
                    value = w[7:]
                else:
                    num_len = 1
                    value = w[5:]
                time_rel = False

                if i >= 1:
                    if u[i - 1] in preps_rel:
                        time_rel = True

                if count_times > 1:
                    j, k = last_time, i
                else:
                    j, k = 0, len(u)

                if value == "now":
                    if any_phrase_in(u[j:k], ['no a', 'kolik je', 'neslyším', 'už mi neříká']):
                        continue
                    else:
                        time_rel = True

                for act_type, time_type, phrases_pos, phrases_neg in test_context:
                    if any_phrase_in(u[j:k], phrases_pos) and not any_phrase_in(u, phrases_neg):
                        break

                if count_times > 1 and not time_type:
                    # use the previous type if there was time before this one
                    time_type = last_time_type
                last_time_type = time_type

                slot = (time_type + ('_time_rel' if time_rel else '_time')).lstrip('_')
                cn.add(1.0, DialogueActItem(act_type, slot, value, alignment=set(range(i, i+num_len))))
                last_time = i + 1

    def parse_date_rel(self, abutterance, cn):
        """Detects the relative date in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        u = abutterance

        confirm = phrase_in(u, ['jede', 'to'])
        deny = phrase_in(u, ['nechci', 'ne'])

        for i, w in enumerate(u):
            if w.startswith("DATE_REL="):
                value = w[9:]

                if confirm:
                    dai = DialogueActItem("confirm", 'date_rel', value, alignment={i})
                elif deny:
                    dai = DialogueActItem("deny", 'date_rel', value, alignment={i})
                else:
                    dai = DialogueActItem("inform", 'date_rel', value, alignment={i})

                if not dai in cn:
                    cn.add(1.0, dai)

    def parse_ampm(self, abutterance, cn):
        """Detects the ampm in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        u = abutterance

        confirm = phrase_in(u, ['jede', 'to'])
        deny = phrase_in(u, ['nechci', 'ne'])

        for i, w in enumerate(u):
            if w.startswith("AMPM="):
                value = w[5:]

                if not (phrase_in(u, 'dobrou')):
                    if confirm:
                        cn.add(1.0, DialogueActItem("confirm", 'ampm', value, alignment={i}))
                    elif deny:
                        cn.add(1.0, DialogueActItem("deny", 'ampm', value, alignment={i}))
                    else:
                        cn.add(1.0, DialogueActItem("inform", 'ampm', value, alignment={i}))

    def parse_vehicle(self, abutterance, cn):
        """Detects the vehicle (transport type) in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        u = abutterance

        confirm = phrase_in(u, 'jede to')
        deny = any_phrase_in(u, ['nechci jet', 'bez použití'])

        for i, w in enumerate(u):
            if w.startswith("VEHICLE="):
                value = w[8:]

                if confirm:
                    cn.add(1.0, DialogueActItem("confirm", 'vehicle', value, alignment={i}))
                elif deny:
                    cn.add(1.0, DialogueActItem("deny", 'vehicle', value, alignment={i}))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'vehicle', value, alignment={i}))

    def parse_task(self, abutterance, cn):
        """Detects the task in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        u = abutterance
        deny = phrase_in(u, ['nechci', 'nehledám'])
        for i, w in enumerate(u):
            if w.startswith("TASK="):
                value = w[5:]
                if deny:
                    cn.add(1.0, DialogueActItem("deny", 'task', value, alignment={i}))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'task', value, alignment={i}))

    def parse_train_name(self, abutterance, cn):
        """Detects the train name in the input abstract utterance.

        :param abutterance:
        :param cn:
        """
        category_label = "TRAIN_NAME="

        u = abutterance

        for i, w in enumerate(u):
            if w.startswith(category_label):
                value = w[len(category_label):]

                cn.add(1.0, DialogueActItem("inform", 'train_name', value))


    def parse_non_speech_events(self, utterance, cn):
        """
        Processes non-speech events in the input utterance.

        :param utterance: the input utterance
        :param cn: The output dialogue act item confusion network.
        :return: None
        """
        u = utterance

        if len(u.utterance) == 0 or "_silence_" == u or "__silence__" == u or "_sil_" == u:
            cn.add(1.0, DialogueActItem("silence", alignment={0}))

        if "_noise_" == u or "_laugh_" == u or "_ehm_hmm_" == u or "_inhale_" == u:
            cn.add(1.0, DialogueActItem("null", alignment={0}))

        if "_other_" == u or "__other__" == u:
            cn.add(1.0, DialogueActItem("other", alignment={0}))

    def parse_meta(self, utterance, abutt_lenghts, cn):
        """
        Detects all dialogue acts which do not generalise its slot values using CLDB.

        NOTE: Use DAIBuilder ('dai' variable) to match words and build DialogueActItem,
            so that the DAI is aligned to corresponding words. If matched words are not
            supposed to be aligned, use PTICSHDCSLU matching method instead.
            Make sure to list negative conditions first, so the following positive
            conditions are not added to alignment, when they shouldn't. E.g.:
            (not any_phrase_in(u, ['dobrý den', 'dobrý večer']) and dai.any_word_in("dobrý"))

        :param utterance: the input utterance
        :param cn: The output dialogue act item confusion network.
        :return: None
        """
        u = utterance
        dai = DAIBuilder(u, abutt_lenghts)

        if (dai.any_word_in('ahoj áhoj nazdar zdar') or
                dai.all_words_in('dobrý den')):
            cn.add(1.0, dai.build("hello"))

        if (dai.any_word_in("nashledanou shledanou schledanou shle nashle sbohem bohem zbohem zbohem konec hledanou "
                            "naschledanou shledanó") or dai.phrase_in("dobrou noc") or
                (not any_word_in(u, "nechci") and dai.phrase_in("ukončit hovor"))):
            cn.add(1.0, dai.build("bye"))

        if len(u) == 1 and dai.any_word_in("čau čauky čaues"):
            cn.add(1.0, dai.build("bye"))

        if not any_word_in(u, 'spojení zastávka stanice možnost varianta'):
            if dai.any_word_in('jiný jiné jiná jiného'):
                cn.add(1.0, dai.build("reqalts"))

        if (dai.any_word_in("od začít začneme začněme začni začněte") and dai.any_word_in("začátku znova znovu") or
                dai.any_word_in("reset resetuj restart restartuj zrušit") or
                not any_word_in(u, "ze") and dai.any_phrase_in(['nové spojení', 'nový spojení', 'nové zadání', 'nový zadání', 'nový spoj']) or
                dai.all_words_in("tak jinak") or dai.any_phrase_in(["tak znova", 'zkusíme to ještě jednou'])):
            cn.add(1.0, dai.build("restart"))
        else:
            dai.clear()
            if not any_word_in(u, 'spojení zastávka stanice možnost spoj nabídnutý poslední nalezená opakuji'):
                if (dai.any_word_in('zopakovat opakovat znova znovu opakuj zopakuj zopakujte zvopakovat') or
                        dai.phrase_in("ještě jednou")):
                    cn.add(1.0, dai.build("repeat"))
            elif dai.any_word_in("zopakuj zopakujte zopakovat opakovat") and dai.phrase_in("poslední větu"):
                cn.add(1.0, dai.build("repeat"))

        if ((len(u) == 1 and dai.any_word_in("pardon pardón promiňte promiň sorry")) or
                dai.any_phrase_in(['omlouvám se', 'je mi líto'])):
            cn.add(1.0, dai.build("apology"))

        if not any_word_in(u, "nechci děkuji"):
            if (dai.any_word_in("nápověda nápovědu pomoc pomoct pomoci pomož pomohla pomohl pomůžete help nevím nevim nechápu") or
                    dai.any_word_in('co') and dai.any_word_in("zeptat říct dělat")):
                cn.add(1.0, dai.build("help"))

        if dai.any_word_in("neslyšíme neslyším halo haló nefunguje cože") or \
                not phrase_in(u, "ano slyšíme se") and dai.phrase_in("slyšíme se"):
            cn.add(1.0, dai.build('canthearyou'))

        if (dai.all_words_in("nerozuměl jsem") or
                dai.all_words_in("nerozuměla jsem") or
                dai.all_words_in("taky nerozumím") or
                dai.all_words_in("nerozumím vám") or
                (len(u) == 1 and dai.any_word_in("nerozumím"))):
            cn.add(1.0, dai.build('notunderstood'))

        if not any_word_in(u, "nerozuměj nechci vzdávám čau možnost konec") and dai.any_word_in("ano jo jasně jojo"):
            cn.add(1.0, dai.build("affirm"))

        if not any_phrase_in(u, ['ne z', 'né do']):
            if (dai.any_word_in("ne né nene nené néé") or
                    dai.any_phrase_in(['nechci to tak', 'to nechci', 'to nehledej', 'no nebyli']) or
                    len(u) == 1 and dai.any_word_in("nejedu nechci") or
                    len(u) == 2 and dai.all_words_in("ano nechci") or
                    dai.all_words_in("to je špatně")):
                cn.add(1.0, dai.build("negate"))

        if dai.any_word_in('díky dikec děkuji dekuji děkuju děkují'):
            cn.add(1.0, dai.build("thankyou"))

        if (not any_word_in(u, "ano") and
                (dai.any_word_in('ok pořádku dobře správně stačí super fajn rozuměl rozuměla slyším') or
                 dai.any_phrase_in(['to je vše', 'je to vše', 'je to všechno', 'to bylo všechno', 'to bude všechno',
                                   'už s ničím', 'už s ničim', 'to jsem chtěl slyšet']) or
                 (not any_phrase_in(u, ['dobrý den', 'dobrý dén', 'dobrý večer']) and dai.any_word_in("dobrý")))):
            cn.add(1.0, dai.build("ack"))

        if dai.any_phrase_in(['chci jet', 'chtěla jet', 'bych jet', 'bych jel', 'bychom jet',
                             'bych tam jet', 'jak se dostanu', 'se dostat']) or \
                dai.any_word_in("trasa, trasou, trasy, trasu, trase"):
            cn.add(1.0, dai.build('inform', 'task', 'find_connection'))

        if dai.any_phrase_in(['jak bude', 'jak dnes bude', 'jak je', 'jak tam bude']):
            cn.add(1.0, dai.build('inform', 'task', 'weather'))

        if any_word_in(u, 'nástupiště kolej koleje'):
            cn.add(1.0, DialogueActItem("inform", "task", "find_platform"))

        if (dai.all_words_in('od to jede') or
                dai.all_words_in('z jake jede') or
                dai.all_words_in('z jaké jede') or
                dai.all_words_in('z jaké zastávky') or
                dai.all_words_in('jaká výchozí') or
                dai.all_words_in('kde začátek') or
                dai.all_words_in('odkud to jede') or
                dai.all_words_in('odkud jede') or
                dai.all_words_in('odkud pojede') or
                dai.all_words_in('od kud pojede')):
            cn.add(1.0, dai.build('request', 'from_stop'))

        if (dai.all_words_in('kam to jede') or
                dai.all_words_in('na jakou jede') or
                dai.all_words_in('do jake jede') or
                dai.all_words_in('do jaké jede') or
                dai.all_words_in('do jaké zastávky') or
                dai.all_words_in('co cíl') or
                dai.all_words_in('jaká cílová') or
                dai.all_words_in('kde konečná') or
                dai.all_words_in('kde konečná') or
                dai.all_words_in("kam jede") or
                dai.all_words_in("kam pojede")):
            cn.add(1.0, dai.build('request', 'to_stop'))

        if not any_word_in(u, 'za budu bude budem přijede přijedete přijedu dojedu dojede dorazí dorazím dorazíte'):
            if (dai.all_words_in("kdy jede") or
                    dai.all_words_in("v kolik jede") or
                    dai.all_words_in("v kolik hodin") or
                    dai.all_words_in("kdy to pojede") or
                    (dai.any_word_in('kdy kolik') and dai.any_word_in('jede odjíždí odjede odjíždíš odjíždíte')) or
                    dai.phrase_in('časový údaj')):
                cn.add(1.0, dai.build('request', 'departure_time'))

        if not any_word_in(u, 'budu bude budem přijede přijedete přijedu dojedu dorazí dorazím dorazíte'):
            if (dai.all_words_in("za jak") and dai.any_word_in('dlouho dlóho') or
                    dai.all_words_in("za kolik minut jede") or
                    dai.all_words_in("za kolik minut pojede") or
                    dai.all_words_in("za jak pojede") and dai.any_word_in('dlouho dlóho')):
                cn.add(1.0, dai.build('request', 'departure_time_rel'))

        if ((dai.all_words_in('kdy tam') and dai.any_word_in('budu bude budem')) or
                (dai.all_words_in('v kolik') and dai.any_word_in('budu bude budem')) or
                dai.all_words_in('čas příjezdu') or
                (dai.any_word_in('kdy kolik') and dai.any_word_in('příjezd přijede přijedete přijedu přijedem '
                                                                  'dojedu dorazí dojede dorazím dorazíte'))):
            cn.add(1.0, dai.build('request', 'arrival_time'))

        if (dai.all_words_in('za jak') and dai.any_word_in('dlouho dlóho') and
                dai.any_word_in('budu bude budem přijedu přijede přijedem přijedete dojedu dorazí dorazím dorazíte') and
                dai.any_phrase_in(['tam', 'v cíli', 'do cíle', 'k cíli', 'cílové zastávce', 'cílové stanici'])):
            cn.add(1.0, dai.build('request', 'arrival_time_rel'))

        if not any_word_in(u, 'za v přestup přestupy'):
            if (dai.all_words_in('jak') and dai.any_word_in('dlouho dlóho') and dai.any_word_in("jede pojede trvá trvat") or
                    dai.all_words_in("kolik minut") and dai.any_word_in("jede pojede trvá trvat")):
                cn.add(1.0, dai.build('request', 'duration'))

        if (dai.all_words_in('kolik je hodin') or
                dai.all_words_in('kolik máme hodin') or
                dai.all_words_in('kolik je teď') or
                dai.all_words_in('kolik je teďka')):
            cn.add(1.0, dai.build('request', 'current_time'))

        if dai.any_word_in('přestupů přestupu přestupy stupňů přestup přestupku přestupky přestupků '
                           'přestupovat přestupuju přestupuji přestupování přestupama přestupem'):
            if dai.any_word_in('čas času dlouho trvá trvají trvat'):
                cn.add(1.0, dai.build('request', 'time_transfers'))
            elif dai.any_word_in('kolik počet kolikrát jsou je'):
                cn.add(1.0, dai.build('request', 'num_transfers'))
            elif dai.any_word_in('nechci bez žádný žádné žáden'):
                cn.add(1.0, dai.build('inform', 'num_transfers', '0'))
            elif dai.any_word_in('jeden jedním jednou'):
                cn.add(1.0, dai.build('inform', 'num_transfers', '1'))
            elif dai.any_word_in('dva dvěma dvěmi dvakrát'):
                cn.add(1.0, dai.build('inform', 'num_transfers', '2'))
            elif dai.any_word_in('tři třema třemi třikrát'):
                cn.add(1.0, dai.build('inform', 'num_transfers', '3'))
            elif dai.any_word_in('čtyři čtyřma čtyřmi čtyřikrát'):
                cn.add(1.0, dai.build('inform', 'num_transfers', '4'))
            elif (dai.any_word_in('libovolně libovolný libovolné')
                  or dai.all_words_in('bez ohledu')
                  or dai.any_phrase_in(['s přestupem', 's přestupy', 's přestupama'])):
                cn.add(1.0, dai.build('inform', 'num_transfers', 'dontcare'))

        if dai.any_phrase_in(['přímý spoj', 'přímé spojení', 'přímé spoje', 'přímý spoje', 'přímej spoj',
                              'přímý spojení', 'jet přímo', 'pojedu přímo', 'dostanu přímo', 'dojedu přímo',
                              'dostat přímo']):
            cn.add(1.0, dai.build('inform', 'num_transfers', '0'))

        if dai.any_word_in('spoj spojení spoje možnost možnosti varianta alternativa cesta cestu cesty '
                           'zpoždění stažení nalezená nabídnuté'):
            if not any_word_in(u, 'první jedna druhá druhý třetí čtvrtá čtvrtý') and dai.any_word_in('libovolný'):
                cn.add(1.0, dai.build("inform", "alternative", "dontcare"))

            if (not any_word_in(u, 'druhá druhý třetí čtvrtá čtvrtý') and not all_words_in(u, 'ještě jedna') and
                    dai.any_word_in('první jedna')):
                cn.add(1.0, dai.build("inform", "alternative", "1"))

            if not any_word_in(u, 'třetí čtvrtá čtvrtý další') and dai.any_word_in('druhé druhá druhý druhou dva'):
                cn.add(1.0, dai.build("inform", "alternative", "2"))

            if dai.any_word_in('třetí tři'):
                cn.add(1.0, dai.build("inform", "alternative", "3"))

            if dai.any_word_in('čtvrté čtvrtá čtvrtý čtvrtou čtyři'):
                cn.add(1.0, dai.build("inform", "alternative", "4"))

            if dai.any_word_in('páté pátou'):
                cn.add(1.0, dai.build("inform", "alternative", "5"))

            if dai.any_word_in("předchozí před"):
                if dai.any_phrase_in(["nechci vědět předchozí", "nechci předchozí"]):
                    cn.add(1.0, dai.build("deny", "alternative", "prev"))
                else:
                    cn.add(1.0, dai.build("inform", "alternative", "prev"))

            elif dai.any_word_in("poslední znovu znova opakovat zopakovat zopakujte zopakování"):
                if dai.any_phrase_in(["nechci poslední"]):
                    cn.add(1.0, dai.build("deny", "alternative", "last"))
                else:
                    cn.add(1.0, dai.build("inform", "alternative", "last"))

            elif (dai.any_word_in("další jiné jiná následující pozdější") or
                    dai.any_phrase_in(['ještě jedno', 'ještě jednu', 'ještě jedna', 'ještě jednou', 'ještě zeptat na jedno'])):
                cn.add(1.0, dai.build("inform", "alternative", "next"))

        if ((len(u) == 1 and dai.any_word_in('další následující následují později')) or
                dai.ending_phrases_in(['další', 'co dál'])):
            cn.add(1.0, dai.build("inform", "alternative", "next"))

        if len(u) == 2 and (dai.all_words_in("a další") or dai.all_words_in("a později")):
            cn.add(1.0, dai.build("inform", "alternative", "next"))

        if len(u) == 1 and dai.any_word_in("předchozí před"):
            cn.add(1.0, dai.build("inform", "alternative", "prev"))

        if dai.any_phrase_in(["jako v dne", "jako ve dne"]):
            cn.add(1.0, dai.build('inform', 'ampm', 'pm'))

        if dai.ending_phrases_in(["od", "z", "z nádraží"]):
            cn.add(1.0, dai.build('inform', 'from', '*'))
        elif dai.ending_phrases_in(["na", "do", "dó"]):
            cn.add(1.0, dai.build('inform', 'to', '*'))
        elif dai.ending_phrases_in(["z zastávky", "z stanice", "výchozí stanice je", "výchozí zastávku"]):
            cn.add(1.0, dai.build('inform', 'from_stop', '*'))
        elif dai.ending_phrases_in(["na zastávku", "ná zastávků", "do zastávky", "do zástavky", "do zastavky"]) :
            cn.add(1.0, dai.build('inform', 'to_stop', '*'))
        elif dai.ending_phrases_in(["přes"]):
            cn.add(1.0, dai.build('inform', 'via', '*'))

    def handle_false_abstractions(self, abutterance):
        """
        Revert false positive alarms of abstraction

        :param abutterance: the abstracted utterance
        :return: the abstracted utterance without false positive abstractions
        """
        #
        abutterance = abutterance.replace(('STOP=Metra',), ('metra',))
        abutterance = abutterance.replace(('STOP=Nádraží',), ('nádraží',))
        abutterance = abutterance.replace(('STOP=SME',), ('sme',))
        abutterance = abutterance.replace(('STOP=Bílá Hora', 'STOP=Železniční stanice',),
                                          ('STOP=Bílá Hora', 'železniční stanice',))
        abutterance = abutterance.replace(('TIME=now', 'bych', 'chtěl'), ('teď', 'bych', 'chtěl'))
        abutterance = abutterance.replace(('STOP=Čím', 'se'), ('čím', 'se',))
        abutterance = abutterance.replace(('STOP=Lužin', 'STOP=Na Chmelnici',), ('STOP=Lužin', 'na', 'STOP=Chmelnici',))
        abutterance = abutterance.replace(('STOP=Konečná', 'zastávka'), ('konečná', 'zastávka',))
        abutterance = abutterance.replace(('STOP=Konečná', 'STOP=Anděl'), ('konečná', 'STOP=Anděl',))
        abutterance = abutterance.replace(('STOP=Konečná stanice', 'STOP=Ládví'), ('konečná', 'stanice', 'STOP=Ládví',))
        abutterance = abutterance.replace(('STOP=Výstupní', 'stanice', 'je'), ('výstupní', 'stanice', 'je'))
        abutterance = abutterance.replace(('STOP=Nová', 'jiné'), ('nové', 'jiné',))
        abutterance = abutterance.replace(('STOP=Nová', 'spojení'), ('nové', 'spojení',))
        abutterance = abutterance.replace(('STOP=Nová', 'zadání'), ('nové', 'zadání',))
        abutterance = abutterance.replace(('STOP=Nová', 'TASK=find_connection'), ('nový', 'TASK=find_connection',))
        abutterance = abutterance.replace(('z', 'CITY=Liberk',), ('z', 'CITY=Liberec',))
        abutterance = abutterance.replace(('do', 'CITY=Liberk',), ('do', 'CITY=Liberec',))
        abutterance = abutterance.replace(('pauza', 'hrozně', 'STOP=Dlouhá',), ('pauza', 'hrozně', 'dlouhá',))
        abutterance = abutterance.replace(('v', 'STOP=Praga',), ('v', 'CITY=Praha',))
        abutterance = abutterance.replace(('na', 'STOP=Praga',), ('na', 'CITY=Praha',))
        abutterance = abutterance.replace(('po', 'STOP=Praga', 'ale'), ('po', 'CITY=Praha',))
        abutterance = abutterance.replace(('jsem', 'v', 'STOP=Metra',), ('jsem', 'v', 'VEHICLE=metro',))
        return abutterance

    def parse_1_best(self, obs, verbose=False, *args, **kwargs):
        """Parse an utterance into a dialogue act.

        :rtype DialogueActConfusionNetwork
        """

        utterance = obs['utt']

        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        if verbose:
            print 'Parsing utterance "{utt}".'.format(utt=utterance)

        res_cn = DialogueActConfusionNetwork()

        dict_da = self.utt2da.get(unicode(utterance), None)
        if dict_da:
            for dai in DialogueAct(dict_da):
                res_cn.add(1.0, dai)
            return res_cn

        utterance = self.preprocessing.normalise_utterance(utterance)
        abutterance, category_labels, abutterance_lenghts = self.abstract_utterance(utterance)

        if verbose:
            print 'After preprocessing: "{utt}".'.format(utt=abutterance)
            print category_labels

        self.parse_non_speech_events(utterance, res_cn)

        utterance = utterance.replace_all(['_noise_'], '').replace_all(['_laugh_'], '').replace_all(['_ehm_hmm_'], '').replace_all(['_inhale_'], '')
        abutterance = abutterance.replace_all(['_noise_'], '').replace_all(['_laugh_'], '').replace_all(['_ehm_hmm_'], '').replace_all(['_inhale_'], '')

        abutterance = self.handle_false_abstractions(abutterance)
        category_labels.add('CITY')
        category_labels.add('VEHICLE')
        category_labels.add('NUMBER')


        if len(res_cn) == 0:
            if 'STOP' in category_labels:
                self.parse_stop(abutterance, res_cn)
            if 'CITY' in category_labels:
                self.parse_city(abutterance, res_cn)
            if 'NUMBER' in category_labels:
                self.parse_number(abutterance)
                if any([word.startswith("TIME") for word in abutterance]):
                    category_labels.add('TIME')
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
            if 'TRAIN_NAME' in category_labels:
                self.parse_train_name(abutterance, res_cn)

            self.parse_meta(utterance, abutterance_lenghts, res_cn)

        return res_cn
