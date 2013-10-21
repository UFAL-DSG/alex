#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import random
import itertools
import copy
import re

from alex.components.slu.da import DialogueAct
from alex.utils.config import load_as_module
from alex.components.nlg.tectotpl.core.run import Scenario
from alex.components.nlg.exceptions import TemplateNLGException
from alex.components.nlg.tools.cs import word_for_number, vocalize_prep
from alex.components.dm.ontology import Ontology


class AbstractTemplateNLG(object):
    """\
    Base abstract class for template-filling generators, providing the
    routines for template loading and selection.

    The generation (i.e. template filling) is left to the derived classes.

    It implements numerous backoff strategies:
    1) it matches the exactly the input dialogue against the templates
    2) if it cannot find exact match, then it tries to find a generic template (slot independent)
    3) if it cannot find a generic template, the it tries to compose
        the template from templates for individual dialogue act items
    """

    def __init__(self, cfg):
        """\
        Constructor, just save a link to the configuration.
        """
        self.cfg = cfg

        self.last_utterance = u""

    def load_templates(self, file_name):
        """\
        Load templates from an external file, which is assumed to be a
        Python source which defines the variable 'templates' as a dictionary
        containing stringified dialog acts as keys and (lists of) templates
        as values.
        """
        try:
            templates = load_as_module(file_name, force=True).templates
            # normalize the templates
            self.templates = {}
            # generalised templates
            self.gtemplates = {}
            for k, v in templates.iteritems():
                da = DialogueAct(k)
                # k.sort()
                self.templates[unicode(da)] = v
                self.gtemplates[unicode(self.get_generic_da(da))] = (da, v)

        except Exception as e:
            raise TemplateNLGException('No templates loaded from %s -- %s!' % (file_name, e))

    def get_generic_da(self, da):
        """\
        Given a dialogue act and a list of slots and values, substitute
        the generic values (starting with { and ending with }) with empty string.
        """
        # copy the instance
        da = copy.deepcopy(da)
        # find matching slots & values
        for dai in da:
            if dai.value and dai.value.startswith('{'):
                # there is match, make it generic
                dai.value = "{%s}" % dai.name
        return da

    def get_generic_da_given_svs(self, da, svs):
        """\
        Given a dialogue act and a list of slots and values, substitute
        the matching slot and values with empty string.
        """
        # copy the instance
        da = copy.deepcopy(da)
        # find matching slots & values
        for name, value in svs:
            for dai in da:
                if dai.name == name and dai.value == value:
                    # there is match, make it generic
                    dai.value = "{%s}" % dai.name
        return da

    def match_generic_templates(self, da, svs):
        """\
        Find a matching template for a dialogue act
        using substitutions in case of the slot values.
        """
        tpl = None

        # try to find increasingly generic templates
        # limit the complexity of the search
        if len(svs) == 0:
            rng = []
        elif len(svs) == 1:
            rng = [1, ]
        elif len(svs) == 2:
            rng = [1, 2, ]
        elif len(svs) == 3:
            rng = [1, 2, 3, ]
        else:
            rng = [1, 2, len(svs) - 1, len(svs)]

        for r in rng:
            for cmb in itertools.combinations(svs, r):
                generic_da = self.get_generic_da_given_svs(da, cmb)
                try:
                    gda, tpls = self.gtemplates[unicode(generic_da)]
                    tpl = self.random_select(tpls)
                except KeyError:
                    continue
                return tpl, gda

        # I did not find anything
        raise TemplateNLGException("No match with generic templates.")

    def random_select(self, tpl):
        """\
        Randomly select alternative templates for generation.

        The selection process is modeled by an embedded list structure
        (a tree like structure).
        In the first level the algorithm selects one of N.
        In the second level, for every item it selects one of M, and joins them together.
        This continues toward the leaves which must be non-list objects.

        There are the following random selection options (only the first three):

        (1)
            {
            'hello()' : u"Hello",
            }

            It will return the "Hello" string.

        (2)
            {
            'hello()' : (u"Hello",
                         u"Hi",
                        ),
            }

            It will return one of the "Hello" or "Hi" strings.


        (2)
            {
            'hello()' : (
                         [
                          (u"Hello.",
                           u"Hi.",
                          )
                          (u"How are you doing?",
                           u"Welcome".,
                          ),
                          u"Speak!",
                         ],

                         u"Hi my friend."
                        ),
            }

            It will return one of the following strings:
                "Hello. How are you doing? Speak!"
                "Hi. How are you doing? Speak!"
                "Hello. Welcome. Speak!"
                "Hi. Welcome. Speak!"
                "Hi my friend"
        """
        if isinstance(tpl, basestring):
            return tpl
        elif isinstance(tpl, tuple):
            tpl_rc_or = random.choice(tpl)

            if isinstance(tpl_rc_or, basestring):
                return tpl_rc_or
            elif isinstance(tpl_rc_or, list):
                tpl_rc_and = []

                for t in tpl_rc_or:
                    tpl_rc_and.append(self.random_select(t))

                return u" ".join(tpl_rc_and).replace(u'  ', u' ')
            elif isinstance(tpl_rc_or, tuple):
                raise TemplateNLGException("Unsupported generation type. "
                                           "At this level, the template cannot be a tuple: template = %s" % unicode(tpl))
        elif isinstance(tpl, list):
            raise TemplateNLGException("Unsupported generation type. "
                                       "At this level, the template must cannot be a list: template = %s" % unicode(tpl))
        else:
            raise TemplateNLGException("Unsupported generation type.")

    def generate(self, da):
        """\
        Generate the natural text output for the given dialogue act.

        First, try to find an exact match with no variables to fill in.
        Then try to find a relaxed match of a more generic template and
        fill in the actual values of the variables.
        """

        try:
            if unicode(da) == 'irepeat()':
                pass
            else:
                # try to return exact match
                self.last_utterance = self.random_select(self.templates[unicode(da)])
        except KeyError:
            # try to find a relaxed match
            svs = da.get_slots_and_values()

            try:
                tpls, mda = self.match_generic_templates(da, svs)
                tpl = self.random_select(tpls)
                svs_mda = mda.get_slots_and_values()

                # update the format names from the generic template
                svsx = []
                for (so, vo), (sg, vg) in zip(svs, svs_mda):

                    if vg.startswith('{'):
                        svsx.append([vg[1:-1], vo])
                    else:
                        svsx.append([so, vo])

                self.last_utterance = self.fill_in_template(tpl, svsx)
            except TemplateNLGException:
                composed_utt = []

                # try to find a template for each dialogue act item and concatenate them
                try:
                    dai_tpl = []
                    for dai in da:
                        try:
                            dai_utt = self.random_select(self.templates[unicode(dai)])
                        except KeyError:
                            # try to find a relaxed match
                            dax = DialogueAct()
                            dax.append(dai)
                            svsx = dax.get_slots_and_values()
                            try:
                                tpls, mda = self.match_generic_templates(dax, svsx)
                                dai_tpl = self.random_select(tpls)
                                dai_utt = self.fill_in_template(dai_tpl, svsx)
                            except TemplateNLGException:
                                dai_utt = unicode(dai)

                        composed_utt.append(dai_utt)

                    self.last_utterance = ' '.join(composed_utt)

                except TemplateNLGException:
                    # nothing to do, I must backoff
                    self.last_utterance = self.backoff(da)

        return self.last_utterance

    def fill_in_template(self, tpl, svs):
        """\
        Fill in the given slot values of a dialogue act into the given
        template. This should be implemented in derived classes.
        """
        raise NotImplementedError()

    def backoff(self, da):
        """\
        Provide an alternative NLG template for the dialogue output which is not covered in the templates.
        This serves as a backoff solution. This should be implemented in derived classes.
        """
        raise NotImplementedError()


class TemplateNLG(AbstractTemplateNLG):
    """\
    A simple text-replacement template NLG implementation with the
    ability to resort to a back-off system if no appropriate template is
    found.
    """

    def __init__(self, cfg):
        super(TemplateNLG, self).__init__(cfg)

        if 'model' in self.cfg['NLG']['Template']:
            self.load_templates(self.cfg['NLG']['Template']['model'])
        self.ontology = Ontology()
        self.rel_time_slots = set()
        self.abs_time_slots = set()
        if 'ontology' in self.cfg['NLG']['Template']:
            self.ontology.load(cfg['NLG']['Template']['ontology'])
            # keep track of relative and absolute time slots
            for slot in self.ontology['slot_attributes']:
                if 'relative_time' in self.ontology['slot_attributes'][slot]:
                    self.rel_time_slots.add(slot)
                elif 'absolute_time' in self.ontology['slot_attributes'][slot]:
                    self.abs_time_slots.add(slot)

    def fill_in_template(self, tpl, svs):
        """\
        Simple text replacement template filling.
        """
        svs_dict = dict(svs)
        # spell out time expressions, if applicable
        for slot, val in svs_dict.iteritems():
            if slot in self.rel_time_slots:
                svs_dict[slot] = self.spell_time(val, relative=True)
            elif slot in self.abs_time_slots:
                svs_dict[slot] = self.spell_time(val, relative=False)
        # fill slots and vocalize prepositions
        return self.vocalize_prepos(tpl.format(**svs_dict))

    HR_ENDING = {1: 'u', 2: 'y', 3: 'y', 4: 'y'}

    def spell_time(self, time, relative):
        """\
        Convert a time expression into words (assuming accusative).

        :param time: The 24hr numerical time value in a string, e.g. '8:05'
        'param relative: If true, time is interpreted as relative, i.e. \
                0:15 will generate '15 minutes' and not '0 hours and \
                15 minutes'.
        :return: Czech time string with all numerals written out as words
        """
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

    def vocalize_prepos(self, text):
        """\
        Vocalize prepositions in the utterance, i.e. 'k', 'v', 'z', 's'
        are changed to 'ke', 've', 'ze', 'se' if appropriate given the
        following word.

        This is mainly needed for time expressions, e.g. "v jednu hodinu"
        (at 1:00), but "ve dvě hodiny" (at 2:00).
        """
        def pairwise(iterable):
            a = iter(iterable)
            return itertools.izip(a, a)
        parts = re.split(r'\b([vkzsVKZS]) ', text)
        text = parts[0]
        for prep, follow in pairwise(parts[1:]):
            text += vocalize_prep(prep, follow) + ' ' + follow
        return text


class TectoTemplateNLG(AbstractTemplateNLG):
    """\
    Template generation using tecto-trees and NLG rules.
    """

    def __init__(self, cfg):
        """\
        Initialization, checking configuration, loading
        templates and NLG rules.
        """
        super(TectoTemplateNLG, self).__init__(cfg)
        # check that the configuration contains everything we need
        if not 'NLG' in self.cfg or not 'TectoTemplate' in self.cfg['NLG']:
            raise TemplateNLGException('No configuration found!')
        mycfg = self.cfg['NLG']['TectoTemplate']
        if not 'model' in mycfg or not 'scenario' in mycfg or \
                not 'data_dir' in mycfg:
            raise TemplateNLGException('NLG scenario, data directory ' +
                                       'and templates must be defined!')
        # load templates
        self.load_templates(mycfg['model'])
        # load NLG system
        self.nlg_rules = Scenario(mycfg)
        self.nlg_rules.load_blocks()

    def fill_in_template(self, tpl, svs):
        """\
        Filling in tecto-templates, i.e. filling-in strings to templates
        and using rules to generate the result.
        """
        tpl = unicode(tpl)
        filled_tpl = tpl.format(**dict(svs))
        return self.nlg_rules.apply_to(filled_tpl)
