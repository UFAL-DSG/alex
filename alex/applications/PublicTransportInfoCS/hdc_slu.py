#!/usr/bin/env python
# encoding: utf8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import copy

from alex.components.asr.utterance import Utterance, UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork

# if there is a change in search parameters from_stop, to_stop, time, then
# reset alternatives


def any_word_in(utterance, words):
    words = words if not isinstance(words, basestring) else words.strip().split()
    for alt_expr in words:
        if  alt_expr in utterance.utterance:
            return True

    return False


def all_words_in(utterance, words):
    words = words if not isinstance(words, basestring) else words.strip().split()
    for alt_expr in words:
        if  alt_expr not in utterance.utterance:
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


class PTICSHDCSLU(SLUInterface):
    def __init__(self, preprocessing, cfg=None):
        super(PTICSHDCSLU, self).__init__(preprocessing, cfg)
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
                #print start, end
                #print f

                if f in self.cldb.form2value2cl:
                    for v in self.cldb.form2value2cl[f]:
                        for c in self.cldb.form2value2cl[f][v]:
                            abs_utts = abs_utts.replace(f, (c.upper() + '='+v,))

                            category_labels.add(c.upper())
                            break
                        else:
                            continue

                        break

                    #print f

                    # skip all substring for this form
                    start = end
                    break
                end -= 1
            else:
                start += 1


        return abs_utts, category_labels

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
                        ('in', set(['pro', ])),
                       ]

        self.parse_waypoint(abutterance, cn, 'CITY=', 'city', phr_wp_types, phr_in=['v', 've'])

    def parse_waypoint(self, abutterance, cn, wp_id, wp_slot_suffix, phr_wp_types, phr_in=None):
        """Detects stops or cities in the input abstract utterance
        (called through parse_city or parse_stop).

        :param abutterance: the input abstract utterance.
        :param cn: The output dialogue act item confusion network.
        """
        u = abutterance
        N = len(u)

        # simple "ne" cannot be included as it collides with negation. "ne [,] chci jet z Motola"
        phr_dai_types = [('confirm', set(['jede to', 'odjíždí to', 'je výchozí']), set()),
                         ('deny',
                          set(['nechci', 'nejedu', 'ne z', 'ne od', 'ne na', 'ne do', 'ne k', 'nikoliv']),
                          set(['nechci ukončit hovor', 'nechci to tak', 'né to nechci', 'ne to nechci', 'nechci nápovědu',
                               'nechci chci', ]))]
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

        preps_abs = set(["v", "ve", "čas", "o", "po", "před", "kolem"])
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

                if value == "now" and not any_phrase_in(u[j:k], ['no a', 'kolik je',
                                                                 'neslyším', 'už mi neříká']):
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

        confirm = phrase_in(u, ['jede', 'to'])
        deny = phrase_in(u, ['nechci', 'ne'])

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

        confirm = phrase_in(u, ['jede', 'to'])
        deny = phrase_in(u, ['nechci', 'ne'])

        for i, w in enumerate(u):
            if w.startswith("AMPM="):
                value = w[5:]

                if not (phrase_in(u, 'dobrou')):
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

        confirm = phrase_in(u, ['jede', 'to'])
        deny = phrase_in(u, ['nechci', 'jet'])

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

        deny = phrase_in(u, ['nechci', 'nehledám'])

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

        if  len(u.utterance) == 0 or "_silence_" == u or "__silence__" == u or "_sil_" == u:
            cn.add(1.0, DialogueActItem("silence"))

        if "_noise_" == u or "_laugh_" == u or "_ehm_hmm_" == u or "_inhale_" == u :
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

        if (any_word_in(u, 'ahoj áhoj nazdar zdar') or
                all_words_in(u, 'dobrý den')):
            cn.add(1.0, DialogueActItem("hello"))

        if (any_word_in(u, "nashledanou shledanou schledanou shle nashle sbohem bohem zbohem zbohem konec hledanou "
                            "naschledanou čau čauky čaues shledanó")):
            cn.add(1.0, DialogueActItem("bye"))

        if not any_word_in(u, 'spojení zastávka stanice možnost varianta'):
            if any_word_in(u, 'jiný jiné jiná jiného'):
                cn.add(1.0, DialogueActItem("reqalts"))

        if not any_word_in(u, 'spojení zastávka stanice možnost spoj nabídnutý poslední nalezená začátku opakuji začneme začněme začni začněte'):
            if (any_word_in(u, 'zopakovat opakovat znova znovu opakuj zopakuj zopakujte') or
                phrase_in(u, "ještě jednou")):
                cn.add(1.0, DialogueActItem("repeat"))

        if phrase_in(u, "zopakuj poslední větu") or \
            phrase_in(u, "zopakujte mi poslední větu") or \
            phrase_in(u, "zopakovat poslední větu"):
            cn.add(1.0, DialogueActItem("repeat"))

        if len(u) == 1 and any_word_in(u, "pardon pardón promiňte"):
            cn.add(1.0, DialogueActItem("apology"))

        if not any_word_in(u, "nechci děkuji"):
            if any_word_in(u, "nápověda nápovědu pomoc pomoct pomoci pomož pomohla pomohl pomůžete help nevím nevim") or \
                all_words_in(u, 'co říct') or \
                all_words_in(u, 'co zeptat'):
                cn.add(1.0, DialogueActItem("help"))

        if any_word_in(u, "neslyšíme neslyším halo haló"):
            cn.add(1.0, DialogueActItem('canthearyou'))

        if all_words_in(u, "nerozuměl jsem") or \
            all_words_in(u, "nerozuměla jsem") or \
            all_words_in(u, "taky nerozumím") or \
            all_words_in(u, "nerozumím vám") or \
            (len(u) == 1 and any_word_in(u, "nerozumím")):
            cn.add(1.0, DialogueActItem('notunderstood'))

        if any_word_in(u, "ano jo jasně") and \
            not any_word_in(u, "nerozuměj nechci vzdávám čau možnost konec") :
            cn.add(1.0, DialogueActItem("affirm"))

        if not any_phrase_in(u, ['ne z', ]):
            if  any_word_in(u, "ne né nene nené") or \
                 phrase_in(u, 'nechci to tak') or \
                         len(u) == 1 and any_word_in(u, "nejedu nechci") or \
                         len(u) == 2 and all_words_in(u, "ano nechci") or \
                 all_words_in(u, "to je špatně"):
                cn.add(1.0, DialogueActItem("negate"))

        if any_word_in(u, 'díky dikec děkuji dekuji děkuju děkují'):
            cn.add(1.0, DialogueActItem("thankyou"))

        if any_word_in(u, 'ok pořádku dobře správně') and \
            not any_word_in(u, "ano"):
            cn.add(1.0, DialogueActItem("ack"))

        if any_word_in(u, "od začít začneme začněme začni začněte") and any_word_in(u, "začátku znova znovu") or \
            any_word_in(u, "reset resetuj restart restartuj") or \
            phrase_in(u, 'nové spojení') and not phrase_in(u, 'spojení ze') or \
            phrase_in(u, 'nový spojení') and not phrase_in(u, 'spojení ze') or \
            phrase_in(u, 'nové zadání') and not any_word_in(u, "ze") or \
            phrase_in(u, 'nový zadání') and not any_word_in(u, "ze") or \
            phrase_in(u, 'nový spoj') and not phrase_in(u, "spoj ze"):
            cn.add(1.0, DialogueActItem("restart"))

        if any_phrase_in(u, ['chci jet', 'chtěla jet', 'bych jet', 'bychom jet',
                             'bych tam jet', ]):
            cn.add(1.0, DialogueActItem('inform', 'task', 'find_connection'))

        if any_phrase_in(u, ['jak bude', 'jak dnes bude', 'jak je', 'jak tam bude']):
            cn.add(1.0, DialogueActItem('inform', 'task', 'weather'))

        if all_words_in(u, 'od to jede') or \
            all_words_in(u, 'z jake jede') or \
            all_words_in(u, 'z jaké jede') or \
            all_words_in(u, 'z jaké zastávky') or \
            all_words_in(u, 'jaká výchozí') or \
            all_words_in(u, 'kde začátek') or \
            all_words_in(u, 'odkud to jede') or \
            all_words_in(u, 'odkud jede') or \
            all_words_in(u, 'odkud pojede') or \
            all_words_in(u, 'od kud pojede'):
            cn.add(1.0, DialogueActItem('request', 'from_stop'))

        if all_words_in(u, 'kam to jede') or \
            all_words_in(u, 'na jakou jede') or \
            all_words_in(u, 'do jake jede') or \
            all_words_in(u, 'do jaké jede') or \
            all_words_in(u, 'do jaké zastávky') or \
            all_words_in(u, 'co cíl') or \
            all_words_in(u, 'jaká cílová') or \
            all_words_in(u, 'kde konečná') or \
            all_words_in(u, 'kde konečná') or \
            all_words_in(u, "kam jede") or \
            all_words_in(u, "kam pojede"):
            cn.add(1.0, DialogueActItem('request', 'to_stop'))

        if not any_word_in(u, 'za budu bude budem přijede přijedete přijedu dojedu dorazí dorazím dorazíte'):
            if all_words_in(u, "kdy jede") or \
                all_words_in(u, "v kolik jede") or \
                all_words_in(u, "v kolik hodin") or \
                all_words_in(u, "kdy to pojede") or \
                (any_word_in(u, 'kdy kolik') and  any_word_in(u, 'jede odjíždí odjede odjíždíš odjíždíte')):
                cn.add(1.0, DialogueActItem('request', 'departure_time'))

        if not any_word_in(u, 'budu bude budem přijede přijedete přijedu dojedu dorazí dorazím dorazíte'):
            if all_words_in(u, "za jak dlouho") or \
                all_words_in(u, "za kolik minut jede") or \
                all_words_in(u, "za kolik minut pojede") or \
                all_words_in(u, "za jak dlouho pojede"):
                cn.add(1.0, DialogueActItem('request', 'departure_time_rel'))

        if (all_words_in(u, 'kdy tam') and any_word_in(u, 'budu bude budem')) or \
            (all_words_in(u, 'v kolik tam') and any_word_in(u, 'budu bude budem')) or \
            (all_words_in(u, 'v kolik hodin') and any_word_in(u, 'budu bude budem')) or \
            all_words_in(u, 'čas příjezdu') or \
            (any_word_in(u, 'kdy kolik') and  any_word_in(u, 'příjezd přijede přijedete přijedu přijedem dojedu dorazí '
                                                             'dorazím dorazíte')):
            cn.add(1.0, DialogueActItem('request', 'arrival_time'))

        if all_words_in(u, 'za jak dlouho tam') and any_word_in(u, "budu bude budem přijedu přijede přijedem přijedete "
                                                                   "dojedu dorazí dorazím dorazíte") or \
            all_words_in(u, 'za jak dlouho budu') and (any_word_in(u, "cílové stanici") or \
                                                           any_word_in(u, "cílové zastávce") or \
                                                           any_word_in(u, 'cíli')):
            cn.add(1.0, DialogueActItem('request', 'arrival_time_rel'))

        if not any_word_in(u, 'za'):
            if all_words_in(u, 'jak dlouho') and any_word_in(u, "jede pojede trvá trvat"):
                cn.add(1.0, DialogueActItem('request', 'duration'))

        if all_words_in(u, 'kolik je hodin') or \
            all_words_in(u, 'kolik máme hodin') or \
            all_words_in(u, 'kolik je teď') or \
            all_words_in(u, 'kolik je teďka'):
            cn.add(1.0, DialogueActItem('request', 'current_time'))

        if any_word_in(u, 'kolik počet kolikrát jsou je') and \
            any_word_in(u, 'přestupů přestupu přestupy stupňů přestup přestupku přestupky přestupků ' +
                        'přestupovat přestupuju přestupuji') and \
            not any_word_in(u, 'čas času'):
            cn.add(1.0, DialogueActItem('request', 'num_transfers'))

        if any_word_in(u, 'spoj spojení spoje možnost možnosti varianta alternativa cesta cestu cesty '
                          'zpoždění stažení nalezená'):
            if any_word_in(u, 'první jedna') and \
                not any_word_in(u, 'druhá druhý třetí čtvrtá čtvrtý'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "1"))

            if any_word_in(u, 'druhé druhá druhý druhou dva')and \
                not any_word_in(u, 'třetí čtvrtá čtvrtý další'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "2"))

            if any_word_in(u, 'třetí tři'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "3"))

            if any_word_in(u, 'čtvrté čtvrtá čtvrtý čtvrtou čtyři'):
                cn.add(1.0, DialogueActItem("inform", "alternative", "4"))

            if any_word_in(u, "poslední znovu znova opakovat zopakovat zopakujte zopakování") and \
                not all_words_in(u, "předchozí"):
                cn.add(1.0, DialogueActItem("inform", "alternative", "last"))

            if any_word_in(u, "další jiné jiná následující pozdější") or \
                phrase_in(u, "ještě jedno") or \
                phrase_in(u, "ještě jednu"):
                cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

            if any_word_in(u, "předchozí před"):
                if phrase_in(u, "nechci vědět předchozí"):
                    cn.add(1.0, DialogueActItem("deny", "alternative", "prev"))
                else:
                    cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if len(u) == 1 and any_word_in(u, 'další následující následují'):
            cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

        if len(u) == 2 and \
            (all_words_in(u, "a další") or  all_words_in(u, "a později")):
            cn.add(1.0, DialogueActItem("inform", "alternative", "next"))

        if len(u) == 1 and any_word_in(u, "předchozí před"):
            cn.add(1.0, DialogueActItem("inform", "alternative", "prev"))

        if phrase_in(u, "jako ve dne"):
            cn.add(1.0, DialogueActItem('inform', 'ampm', 'pm'))

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
            category_labels = dict()

        # handle false positive alarms of abstraction
        abutterance = abutterance.replace(('STOP=Výstupní', 'stanice', 'je'), ('výstupní', 'stanice', 'je'))
        abutterance = abutterance.replace(('STOP=Nová','spojení'), ('nové', 'spojení',))
        abutterance = abutterance.replace(('STOP=Nová','zadání'), ('nové', 'zadání',))
        abutterance = abutterance.replace(('STOP=Nová','TASK=find_connection'), ('nový', 'TASK=find_connection',))
        abutterance = abutterance.replace(('z', 'CITY=Liberk',), ('z', 'CITY=Liberec',))
        abutterance = abutterance.replace(('do', 'CITY=Liberk',), ('do', 'CITY=Liberec',))
        abutterance = abutterance.replace(('v', 'STOP=Praga',), ('v', 'CITY=Praha',))
        category_labels.add('CITY')

        # print 'After preprocessing: "{utt}".'.format(utt=abutterance)
        # print category_labels

        res_cn = DialogueActConfusionNetwork()

        self.parse_non_speech_events(utterance, res_cn)

        if len(res_cn) == 0:
            # remove non speech events, they are not relevant for SLU
            abutterance = abutterance.replace_all('_noise_', '').replace_all('_laugh_', '').replace_all('_ehm_hmm_', '').replace_all('_inhale_', '')

            if 'STOP' in category_labels:
                self.parse_stop(abutterance, res_cn)
            if 'CITY' in category_labels:
                self.parse_city(abutterance, res_cn)
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
