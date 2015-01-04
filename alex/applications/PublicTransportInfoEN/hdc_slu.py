#!/usr/bin/env python
# encoding: utf8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import copy
import traceback

from alex.components.asr.utterance import Utterance, UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork

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
            return pos, pos + len(phrase)
    return -1, -1


def any_phrase_in(utterance, phrases):
    return first_phrase_span(utterance, phrases) != (-1, -1)


class PTIENHDCSLU(SLUInterface):
    def __init__(self, preprocessing, cfg=None):
        super(PTIENHDCSLU, self).__init__(preprocessing, cfg)
        self.cldb = self.preprocessing.cldb

    def abstract_utterance(self, utterance):
        """
        Return a list of possible abstractions of the utterance.

        :param utterance: an Utterance instance
        :return: a list of abstracted utterance, form, value, category label tuples
        """

        abs_utts = copy.deepcopy(utterance)
        category_labels = set()

        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end > start:
                f = tuple(utterance[start:end])
                # print start, end
                # print f

                if f in self.cldb.form2value2cl:
                    for v in self.cldb.form2value2cl[f]:
                        slots = self.cldb.form2value2cl[f][v]
                        # todo - fix this hack
                        # # TODO: add STREET handling!
                        # if "street" in slots:
                        #     abs_utts = abs_utts.replace(f, ('STOP='+v,))
                        #     category_labels.add('STOP')
                        # elif "stop" in slots and ("city" in slots or "street" in slots):
                        if "stop" in slots and ("city" in slots or "street" in slots):
                            abs_utts = abs_utts.replace(f, ('STOP='+v,))
                            category_labels.add('STOP')
                        else:
                            for c in slots:
                                abs_utts = abs_utts.replace(f, (c.upper() + '='+v,))
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


        return abs_utts, category_labels

    def __repr__(self):
        return "PTIENHDCSLU({preprocessing}, {cfg})".format(preprocessing=self.preprocessing, cfg=self.cfg)

    def parse_street(self, abutterance, cn):
        """ Detects street in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        # regular parsing
        phr_wp_types = [('from', set(['from', 'beginning', 'start', 'starting', 'origin', 'standing in', 'standing at',  # of, off
                                      'originated', 'originating', 'origination', 'initial', 'i am at', 'i am in',
                                      'leave', ])),
                        ('to', set(['to', 'into', 'in', 'end', 'ending', 'terminal', 'final',
                                    'target', 'output', 'exit', 'destination', 'be at'])),
                        ('via', set(['via', 'through', 'transfer', 'transferring', 'interchange', ]))]  # change line

        #TODO: here we need to support more than one initial and destination point if it is a street!
        self.parse_waypoint(abutterance, cn, 'STREET=', 'street', phr_wp_types)

    def parse_stop(self, abutterance, cn):
        """ Detects stops in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        # regular parsing
        phr_wp_types = [('from', set(['from', 'beginning', 'start', 'starting', 'origin', 'standing in', 'standing at',  # of, off
                                      'originated', 'originating', 'origination', 'initial', 'i am at', 'i am in',
                                      'leave', ])),
                        ('to', set(['to', 'into', 'in', 'end', 'ending', 'terminal', 'final',
                                    'target', 'output', 'exit', 'destination', 'be at'])),
                        ('via', set(['via', 'through', 'transfer', 'transferring', 'interchange', ]))]  # change line

        self.parse_waypoint(abutterance, cn, 'STOP=', 'stop', phr_wp_types)

    def parse_state(self, abutterance, cn):
        """ Detects state in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        for i, w in enumerate(abutterance):
            if w.startswith("STATE="):
                value = w[6:]
                cn.add(1.0, DialogueActItem("inform", 'in_state', value))


    def parse_city(self, abutterance, cn):
        """ Detects stops in the input abstract utterance.

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """

        # regular parsing
        phr_wp_types = [('from', set(['from', 'beginning', 'start', 'starting', 'origin', # of, off
                                      'originated', 'originating', 'origination', 'initial', ])), # I'm at, I'm in ?
                        ('to', set(['to', 'into', 'in' 'end', 'ending', 'terminal', 'final',
                                    'target', 'output', 'exit', 'destination',])),
                        ('via', set(['via', 'through', 'transfer', 'transferring', 'interchange' ])),
                        ('in', set(['for', 'after', 'in', 'at'])),  # ? ['pro', 'po']
                       ]

        self.parse_waypoint(abutterance, cn, 'CITY=', 'city', phr_wp_types, phr_in=['in', 'at'])

    def parse_waypoint(self, abutterance, cn, wp_id, wp_slot_suffix, phr_wp_types, phr_in=None):
        """Detects stops or cities in the input abstract utterance
        (called through parse_city or parse_stop).

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """
        u = abutterance
        N = len(u)

        # simple "not" cannot be included as it collides with negation. "I do not want [,] go from Brooklyn"
        phr_dai_types = [('confirm', set(['it departs', 'departs from', 'depart from',  # 'leave', 'leaves',
                                          'is the starting',]), set()),
                         ('deny',
                          set(['not from', 'not at', 'not in', 'not on', 'not to', 'not into', 'and not',
                               'not the', 'rather than']),  # don't, doesn't?
                          set(['not at all' 'not wish', 'not this way', 'no not that', 'not need help',
                               'not want', ]))]
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
                # test longer following context - hack for catching "_ is the terminal station."
                if not wp_types:
                    if any_phrase_in(u[i:i + 5], phr_wp_types[0][1]):  # and not another STOP= (wp_type asi?) in i, i + 6 -> ok, jinak to nad tímhle
                        wp_types.add('from')
                    elif any_phrase_in(u[i:i + 5], phr_wp_types[1][1]):
                        wp_types.add('to')
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
                    cn.add(1.0, DialogueActItem(dai_type, wp_types.pop() + '_' + wp_slot_suffix, wp_name))
                # backoff 1: add both 'from' and 'to' waypoint slots
                elif 'from' in wp_types and 'to' in wp_types:
                    cn.add(0.501, DialogueActItem(dai_type, 'from_' + wp_slot_suffix, wp_name))
                    cn.add(0.499, DialogueActItem(dai_type, 'to_' + wp_slot_suffix, wp_name))
                # backoff 2: let the DM decide in context resolution
                else:
                    cn.add(1.0, DialogueActItem(dai_type, '', wp_name))

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

    def parse_time(self, abutterance, cn):
        """Detects the time in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance

        preps_abs = set(["at", "time", "past", "after", "between", "before", "in", "around", "about", "for"])
        preps_rel = set(["in", ])

        # list of positive, negative (contains(positive) & !contains(negative))
        test_context = [('confirm', 'departure',
                         ['it leaves', 'it departures', 'it starts', 'is starting', 'is leaving', 'is departuring',
                          'departure point'],
                         []),
                        ('confirm', 'arrival',
                         ['it arrives', 'is arriving', 'will arrive', 'is coming', 'it comes', 'will come',
                          'arrival is'],  # will reach
                         []),
                        ('confirm', '',
                         ['it is', 'you think', 'positive'],
                         []),
                        ('deny', 'departure',
                         ['not leaving', 'not leave', 'not departing', 'not departure', 'not starting',
                          'not start', 'not want to go from'],
                         []),
                        ('deny', 'arrival',
                         ['not arriving', 'not arrive', 'not come', 'not coming', 'not want to arrive',
                          'not want to come', 'not want to go to', 'not want to arrive'],
                         []),
                        ('deny', '',
                         ['no', 'not want', 'negative'],
                         []),
                        ('inform', 'departure',
                         ['TASK=find_connection', 'departure', 'departing', 'departs', 'departs from', 'leaving',
                          'leaves', 'starts', 'starting', 'goes', 'would go', 'will go', 'VEHICLE=tram',
                          'want to go', 'want to leave', 'want to take', 'want to travel', 'how can i get',
                          'wanted to go', 'wanted to leave', 'wanted to take', 'wanted to travel',
                          'how do i get', 'would like to go', 'i am at', 'i am in', ],
                         ['arrival', 'arrive', 'arriving', 'want to be at', 'wanted to be at', 'like to be at', ]),
                        ('inform', 'arrival',
                         ['arrival', 'arrive', 'get to', 'to get', 'arriving', 'want to be at', 'wanted to be at', 'like to be at', ],
                         []),
                        ('inform', '',
                         [],
                         []),
                        ]

        count_times = 0
        for i, w in enumerate(u):
            if w.startswith("TIME="):
                count_times += 1

        last_time_type = ''
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

                if count_times > 1:
                    j, k = last_time, i
                else:
                    j, k = 0, len(u)

                if value == "now" and not any_phrase_in(u[j:k], ['so what', 'what is the time', 'whats the time',
                                                                 'can not hear', 'no longer telling me']):
                    time_rel = True

                if time_abs or time_rel:
                    for act_type, time_type, phrases_pos, phrases_neg in test_context:
                        if any_phrase_in(u[j:k], phrases_pos) and not any_phrase_in(u, phrases_neg):
                            break

                    if count_times > 1 and not time_type:
                        # use the previous type if there was time before this one
                        time_type = last_time_type

                    last_time_type = time_type

                    slot = (time_type + ('_time_rel' if time_rel else '_time')).lstrip('_')
                    cn.add(1.0, DialogueActItem(act_type, slot, value))

                last_time = i + 1

    def parse_date_rel(self, abutterance, cn):
        """Detects the relative date in the input abstract utterance.

        :param abutterance:
        :param cn:
        """

        u = abutterance

        confirm = phrase_in(u, ['it', 'does'])
        deny = phrase_in(u, ['not', 'want'])

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

        confirm = phrase_in(u, ['it', 'does'])
        deny = phrase_in(u, ['not', 'want'])

        for i, w in enumerate(u):
            if w.startswith("AMPM="):
                value = w[5:]

                if not (phrase_in(u, 'good night')):
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

        confirm = phrase_in(u, ['it', 'does'])
        deny = phrase_in(u, ['not', 'want'])

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

        deny = phrase_in(u, ['not want', 'don\'t want', 'not looking for'])

        for i, w in enumerate(u):
            if w.startswith("TASK="):
                value = w[5:]

                if deny:
                    cn.add(1.0, DialogueActItem("deny", 'task', value))
                else:
                    cn.add(1.0, DialogueActItem("inform", 'task', value))

    def parse_non_speech_events(self, utterance, cn):
        """
        Processes non-speech events in the input utterance.

        :param utterance:
        :param cn:
        :return: None
        """
        u = utterance

        if len(u.utterance) == 0 or "_silence_" == u or "__silence__" == u or "_sil_" == u:
            cn.add(1.0, DialogueActItem("silence"))

        if "_noise_" == u or "_laugh_" == u or "_ehm_hmm_" == u or "_inhale_" == u:
            cn.add(1.0, DialogueActItem("null"))

        if "_other_" == u or "__other__" == u:
            cn.add(1.0, DialogueActItem("other"))

    def parse_meta(self, utterance, cn):
        """
        Detects all dialogue acts which do not generalise its slot values using CLDB.

        :param utterance:
        :param cn:
        :return: None
        """
        u = utterance

        if (any_word_in(u, 'ahoy hello hey hi greetings') or
                any_phrase_in(u, ['good day', "what's up", 'what is up'])):
            cn.add(1.0, DialogueActItem("hello"))

        if (any_word_in(u, "bye byebye seeya goodbye") or
                any_phrase_in(u, ['good bye', 'see you'])):
            cn.add(1.0, DialogueActItem("bye"))

        if not any_word_in(u, 'connection station option'):
            if any_word_in(u, 'different another') or\
                    phrase_in(u, 'anything else'):
                cn.add(1.0, DialogueActItem("reqalts"))

        if not any_word_in(u, 'connection station option options last offer offered found beginning begin where going'):
            if (any_word_in(u, 'repeat again') or
                phrase_in(u, "come again") or
                phrase_in(u, "once more")):
                cn.add(1.0, DialogueActItem("repeat"))

        if phrase_in(u, "repeat the last sentence") or \
            phrase_in(u, "repeat what you've") or \
            phrase_in(u, "repeat what you have"):
            cn.add(1.0, DialogueActItem("repeat"))

        if len(u) == 1 and any_word_in(u, "excuse pardon sorry apology, apologise, apologies"):
            cn.add(1.0, DialogueActItem("apology"))

        if not any_word_in(u, "dont want thank"):
            if any_word_in(u, "help hint"):
                cn.add(1.0, DialogueActItem("help"))

        if any_word_in(u, "hallo") or \
                all_words_in(u, 'not hear you'):

            cn.add(1.0, DialogueActItem('canthearyou'))

        if all_words_in(u, "did not understand") or \
            all_words_in(u, "didn\'t understand") or \
            all_words_in(u, "speek up") or \
            all_words_in(u, "can not hear you") or \
            (len(u) == 1 and any_word_in(u, "can\'t hear you")):
            cn.add(1.0, DialogueActItem('notunderstood'))

        if any_word_in(u, "yes yeah sure correct") and \
            not any_word_in(u, "end over option offer surrender") :
            cn.add(1.0, DialogueActItem("affirm"))

        if not any_phrase_in(u, ['not from', ]):
            if any_word_in(u, "no not nope nono") or \
                 phrase_in(u, 'do not want') or \
                         len(u) == 2 and all_words_in(u, "not want") or \
                         len(u) == 3 and all_words_in(u, "yes do not") or \
                 all_words_in(u, "is wrong"):
                cn.add(1.0, DialogueActItem("negate"))

        if any_word_in(u, 'thanks thankyou thank cheers'):
            cn.add(1.0, DialogueActItem("thankyou"))

        if any_word_in(u, 'ok right well correct fine') and \
            not any_word_in(u, "yes"):
            cn.add(1.0, DialogueActItem("ack"))

        if any_word_in(u, "from begin begins start starting") and any_word_in(u, "beginning scratch over") or \
            any_word_in(u, "reset restart reboot") or \
            phrase_in(u, 'new entry') or \
            phrase_in(u, 'new connection') and not phrase_in(u, 'connection from') or \
            phrase_in(u, 'new connection') and not phrase_in(u, 'from') or \
            phrase_in(u, 'new link') and not any_word_in(u, "from"):
            cn.add(1.0, DialogueActItem("restart"))

        if any_phrase_in(u, ['want to go', 'like to go', 'want to get', 'would like to get', 'want to take', 'want to travel', ]):
            cn.add(1.0, DialogueActItem('inform', 'task', 'find_connection'))

        if any_phrase_in(u, ['what is weather', 'what is the weather', 'will be the weather', 'the forecast']):
            cn.add(1.0, DialogueActItem('inform', 'task', 'weather'))

        if all_words_in(u, 'where does it start') or \
            all_words_in(u, 'what is the initial') or \
            all_words_in(u, 'where departure ') or \
            all_words_in(u, 'where departuring') or \
            all_words_in(u, 'where departures') or \
            all_words_in(u, 'where starts') or \
            all_words_in(u, 'where goes from') or \
            all_words_in(u, 'where does go from') or \
            all_words_in(u, 'from what station') or \
            all_words_in(u, 'what is the starting') or \
            all_words_in(u, 'where will from'):
            cn.add(1.0, DialogueActItem('request', 'from_stop'))

        if all_words_in(u, 'where does it arrive') or \
            all_words_in(u, 'where does it stop') or \
            all_words_in(u, 'where stopping') or \
            all_words_in(u, 'where going') or \
            all_words_in(u, 'where arriving') or \
            all_words_in(u, 'to what station') or \
            all_words_in(u, 'at which station arrive') or \
            all_words_in(u, 'what is target') or \
            all_words_in(u, 'where is target') or \
            all_words_in(u, 'where destination') or \
            all_words_in(u, 'where terminates') or \
            all_words_in(u, "where terminal") or \
            all_words_in(u, "where terminate"):
            cn.add(1.0, DialogueActItem('request', 'to_stop'))

        if not any_phrase_in(u, ['will be', 'will arrive', 'will stop', 'will get to']):
            if (any_phrase_in(u, ["what time"]) and any_phrase_in(u, ["is the", "does", ])) or \
                any_phrase_in(u, ["when does", "when is", ]) or \
                (all_words_in(u, 'when time') and any_word_in(u, 'leave departure go')):
                cn.add(1.0, DialogueActItem('request', 'departure_time'))

        if not any_phrase_in(u, ['will be', 'arrive', 'arrives', 'arriving', 'arrival', 'will stop', 'get', 'gets',
            'destination', 'target station', 'terminal station', ]):
            if all_words_in(u, "how") and any_word_in(u, "till until before"):
                cn.add(1.0, DialogueActItem('request', 'departure_time_rel'))

        if (all_words_in(u, 'when will') and any_word_in(u, 'be arrive')) or \
            (all_words_in(u, 'when will i') and any_word_in(u, 'be arrive')) or \
            (all_words_in(u, 'what time will') and any_word_in(u, 'be arrive')) or \
            all_words_in(u, 'time of arrival') or (any_word_in(u, 'when time') and any_word_in(u, 'arrival arrive')):
            cn.add(1.0, DialogueActItem('request', 'arrival_time'))

#tohle celý přepsat, žádný any_word_in 'fráze', a vůbec je to nějaký divný tady kolem
        if all_words_in(u, 'how') and any_word_in(u, 'till until before') and \
            any_phrase_in(u, ['will be', 'arrive', 'arrives', 'arriving', 'arrival', 'will stop', 'get',
                              'gets', 'destination', 'target station', 'terminal station', ]):
            cn.add(1.0, DialogueActItem('request', 'arrival_time_rel'))

        if not any_word_in(u, 'till until'):
            if all_words_in(u, 'how long') and any_phrase_in(u, ['does it take', 'will it take', 'travel']):
                cn.add(1.0, DialogueActItem('request', 'duration'))

        if any_phrase_in(u, ['what time is it', 'what is the time', "what's the time", 'whats the time', 'what time do we have']):
            cn.add(1.0, DialogueActItem('request', 'current_time'))

        if (all_words_in(u, 'how many') or all_words_in(u, 'number of')) and \
            any_word_in(u, 'transfer transfers transformer transformers transferring changing change changes'
                           'interchange interchanging interchanges') and \
            not any_word_in(u, 'time'):
            cn.add(1.0, DialogueActItem('request', 'num_transfers'))

        if any_word_in(u, 'connection alternatives alternative option options found choice'):
            if any_word_in(u, 'arbitrary') and \
                not any_word_in(u, 'first second third fourth one two three four'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "dontcare"))

            if any_word_in(u, 'first one') and \
                not any_word_in(u, 'second third fourth two three four'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "1"))

            if any_word_in(u, 'second two')and \
                not any_word_in(u, 'third fourth next'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "2"))

            if any_word_in(u, 'third three'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "3"))

            if any_word_in(u, 'fourth four'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "4"))

            if any_word_in(u, "last before latest lattermost bottom repeat again") and \
                not all_words_in(u, "previous precedent"):
                cn.add(1.0, DialogueActItem("inform", "alternative", "last"))

            if any_word_in(u, "next different following subsequent later") or \
                phrase_in(u, "once more") or \
                phrase_in(u, "the next one"):
                cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

            if any_word_in(u, "previous precedent"):
                if phrase_in(u, "not want to know previous"):
                    cn.add(1.0, DialogueActItem("deny", "alternative", "prev"))
                else:
                    cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if len(u) == 1 and any_word_in(u, 'next following'):
            cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

        if len(u) == 2 and \
            (all_words_in(u, "and the following") or all_words_in(u, "and afterwards") or
             all_words_in(u, "and later")):
            cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

        if len(u) == 1 and any_word_in(u, "previous precedent"):
            cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if any_phrase_in(u, ["by day", "of the day"]):
            cn.add(1.0, DialogueActItem('inform', 'ampm', 'pm'))

    def printStackTrace(self):
        print "______________________________________"
        for line in traceback.format_stack():
            print line.strip()
        print "______________________________________"

    def parse_1_best(self, obs, verbose=False):

        """Parse an utterance into a dialogue act."""
        utterance = obs['utt']

        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        # print 'Parsing utterance "{utt}".'.format(utt=utterance)
        if verbose:
            print 'Parsing utterance "{utt}".'.format(utt=utterance)

        if self.preprocessing:
            # the text normalisation
            utterance = self.preprocessing.normalise_utterance(utterance)

            abutterance, category_labels = self.abstract_utterance(utterance)

            if verbose:
                print 'After preprocessing: "{utt}".'.format(utt=abutterance)
                print category_labels
        else:
            abutterance = ""
            category_labels = dict()

        # handle false positive alarms of abstraction

        abutterance = abutterance.replace(('how', 'CITY=Many'), ('how', 'many'))
        abutterance = abutterance.replace(('CITY=Tell', 'me'), ('tell', 'me'))
        abutterance = abutterance.replace(('CITY=Transfer',), ('transfer',))
        if 'CITY=Ohio' in abutterance[:]:
            abutterance = abutterance.replace(('CITY=Ohio',), ('STATE=Ohio',))
            category_labels.remove('CITY')
            category_labels.add('STATE')
        if 'CITY=California' in abutterance[:]:
            abutterance = abutterance.replace(('CITY=California',), ('STATE=California',))
            category_labels.remove('CITY')
            category_labels.add('STATE')
        if 'CITY=Washington' in abutterance[:]:
            abutterance = abutterance.replace(('CITY=Washington',), ('STATE=Washington',))
            category_labels.remove('CITY')
            category_labels.add('STATE')
        if 'CITY=Maryland' in abutterance[:]:
            abutterance = abutterance.replace(('CITY=Maryland',), ('STATE=Maryland',))
            category_labels.remove('CITY')
            category_labels.add('STATE')

        # abutterance = abutterance.replace(('STOP=Metra',), ('metra',))
        # abutterance = abutterance.replace(('STOP=Nádraží',), ('nádraží',))
        # abutterance = abutterance.replace(('STOP=SME',), ('sme',))
        # abutterance = abutterance.replace(('STOP=Bílá Hora', 'STOP=Železniční stanice',), ('STOP=Bílá Hora', 'železniční stanice',))
        #
        # abutterance = abutterance.replace(('TIME=now','bych', 'chtěl'), ('teď', 'bych', 'chtěl'))
        # abutterance = abutterance.replace(('STOP=Lužin','STOP=Na Chmelnici',), ('STOP=Lužin','na','STOP=Chmelnici',))
        # abutterance = abutterance.replace(('STOP=Konečná','zastávka'), ('konečná', 'zastávka',))
        # abutterance = abutterance.replace(('STOP=Konečná','STOP=Anděl'), ('konečná', 'STOP=Anděl',))
        # abutterance = abutterance.replace(('STOP=Konečná stanice','STOP=Ládví'), ('konečná', 'stanice', 'STOP=Ládví',))
        # abutterance = abutterance.replace(('STOP=Output', 'station', 'is'), ('output', 'station', 'is'))
        # abutterance = abutterance.replace(('STOP=Nová','jiné'), ('nové', 'jiné',))
        # abutterance = abutterance.replace(('STOP=Nová','spojení'), ('nové', 'spojení',))
        # abutterance = abutterance.replace(('STOP=Nová','zadání'), ('nové', 'zadání',))
        # abutterance = abutterance.replace(('STOP=Nová','TASK=find_connection'), ('nový', 'TASK=find_connection',))
        # abutterance = abutterance.replace(('z','CITY=Liberk',), ('z', 'CITY=Liberec',))
        # abutterance = abutterance.replace(('do','CITY=Liberk',), ('do', 'CITY=Liberec',))
        # abutterance = abutterance.replace(('pauza','hrozně','STOP=Dlouhá',), ('pauza','hrozně','dlouhá',))
        # abutterance = abutterance.replace(('v','STOP=Praga',), ('v', 'CITY=Praha',))
        # abutterance = abutterance.replace(('na','STOP=Praga',), ('na', 'CITY=Praha',))
        # abutterance = abutterance.replace(('po','STOP=Praga', 'ale'), ('po', 'CITY=Praha',))
        # abutterance = abutterance.replace(('jsem','v','STOP=Metra',), ('jsem', 'v', 'VEHICLE=metro',))
        # category_labels.add('CITY')
        # category_labels.add('VEHICLE')

        # print 'After preprocessing: "{utt}".'.format(utt=abutterance)
        # print category_labels

        res_cn = DialogueActConfusionNetwork()

        self.parse_non_speech_events(utterance, res_cn)

        if len(res_cn) == 0:
            # remove non speech events, they are not relevant for SLU
            abutterance = abutterance.replace_all('_noise_', '').replace_all('_laugh_', '').replace_all('_ehm_hmm_', '').replace_all('_inhale_', '')

            if 'STREET' in category_labels:  # TODO: handle streets separately!
                self.parse_street(abutterance, res_cn)
            if 'STOP' in category_labels:
                self.parse_stop(abutterance, res_cn)
            if 'CITY' in category_labels:
                self.parse_city(abutterance, res_cn)
            if 'STATE' in category_labels:
                self.parse_state(abutterance, res_cn)
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
