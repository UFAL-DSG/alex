#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import autopath

from alex.components.slu.base import SLUPreprocessing
from alex.components.asr.utterance import Utterance
from alex.utils.czech_stemmer import cz_stem
from alex.components.nlg.template import TemplateNLGPreprocessing
from alex.components.nlg.tools.cs import word_for_number


class PTICSSLUPreprocessing(SLUPreprocessing):
    """
    Extends SLUPreprocessing for some transformations specific for Czech:
        - devocalisation of prepositions
        (- stemming).

    """
    def __init__(self, *args, **kwargs):
        super(PTICSSLUPreprocessing, self).__init__(*args, **kwargs)

        num_norms = []
        for num in xrange(60):
            num_norms.append(([unicode(num)], [word_for_number(num, 'F1')]))
        self.text_normalization_mapping += num_norms

        self.text_normalization_mapping += [
            (['ve'], ['v']),
            (['ke'], ['k']),
            (['ku'], ['k']),
            (['ze'], ['z']),
            (['se'], ['s']),
            (['andělu'], ['anděla']),
            (['zvonařky'], ['zvonařka']),
            (['zvonařku'], ['zvonařka']),
            (['bucharovy'], ['bucharova']),
            (['bucharovu'], ['bucharova']),
            (['barandov'], ['barrandov']),
            (['dejvic'], ['dejvická']),
            (['dejvice'], ['dejvická']),
            (['litňanská'], ['letňanská']),
            (['palacké'], ['palackého']),
            (['ajpí', 'pavlova'],   ['i','p','pavlova']),
            (['aj','pí','pavlova'], ['i','p','pavlova']),
            (['ípé','pa', 'pavlova'], ['i','p','pavlova']),
            (['í','pé','pa', 'pavlova'], ['i','p','pavlova']),
            (['i','p', 'pavlovy'], ['i','p','pavlova']),
            (['ajpák'],   ['i','p','pavlova']),
            (['ajpáku'],  ['i','p','pavlova']),
            (['ípák'],    ['i','p','pavlova']),
            (['ípáku'],   ['i','p','pavlova']),
            (['čaplinovo'], ['chaplinovo']),
            (['čaplinova'], ['chaplinova']),
            (['zologická'],   ['zoologická']),
            (['zoo','praha'], ['zoologická','zahrada']),
            (['na','ruzyň'],           ['na','ruzyňské','letiště']),
            (['václav','havel'],       ['letiště','václava','havla']),
            (['václava','havla'],      ['letiště','václava','havla']),
            (['ruzyňské','letiště'],   ['letiště','václava','havla']),
            (['letiště','v','ruzyni'], ['letiště','václava','havla']),
        ]

    def normalise_utterance(self, utterance):
        utterance = super(PTICSSLUPreprocessing, self).normalise_utterance(utterance)
        #utterance = Utterance(" ".join(map(cz_stem, utterance)))
        return utterance


class PTICSNLGPreprocessing(TemplateNLGPreprocessing):
    """Template NLG preprocessing routines for Czech public transport information.

    This serves mainly for spelling out relative and absolute time expressions
    in Czech.
    """

    def __init__(self, ontology):
        super(PTICSNLGPreprocessing, self).__init__(ontology)
        # keep track of relative and absolute time slots
        self.rel_time_slots = set()
        self.abs_time_slots = set()
        # load their lists from the ontology
        if 'slot_attributes' in self.ontology:
            for slot in self.ontology['slot_attributes']:
                if 'relative_time' in self.ontology['slot_attributes'][slot]:
                    self.rel_time_slots.add(slot)
                elif 'absolute_time' in self.ontology['slot_attributes'][slot]:
                    self.abs_time_slots.add(slot)

    def preprocess(self, svs_dict):
        # spell out time expressions, if applicable
        for slot, val in svs_dict.iteritems():
            if slot in self.rel_time_slots:
                svs_dict[slot] = self.spell_time(val, relative=True)
            elif slot in self.abs_time_slots:
                svs_dict[slot] = self.spell_time(val, relative=False)
        return svs_dict

    HR_ENDING = {1: 'u', 2: 'y', 3: 'y', 4: 'y'}

    def spell_time(self, time, relative):
        """\
        Convert a time expression into words (assuming accusative).

        :param time: The 24hr numerical time value in a string, e.g. '8:05'
        :param relative: If true, time is interpreted as relative, i.e. \
                0:15 will generate '15 minutes' and not '0 hours and \
                15 minutes'.
        :return: Czech time string with all numerals written out as words
        """
        if ':' not in time:  # 'now' and similar
            return time
        hours, mins = map(int, time.split(':'))
        time_str = []
        if not (relative and hours == 0):
            hr_id = 'hodin' + self.HR_ENDING.get(hours, '')
            hours = word_for_number(hours, 'F4')
            time_str.extend((hours, hr_id))
        if mins == 0 and not relative:
            return ' '.join(time_str)
        if time_str:
            time_str.append('a')
        min_id = 'minut' + self.HR_ENDING.get(mins, '')
        mins = word_for_number(mins, 'F4')
        return ' '.join(time_str + [mins, min_id])
