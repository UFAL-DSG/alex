#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import random
import itertools
import copy

from alex.components.slu.da import DialogueAct
from alex.utils.exception import TemplateNLGException
from alex.utils.config import load_as_module
from alex.components.nlg.tectotpl.core.run import Scenario


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
            for k, v in templates.iteritems():
                k = DialogueAct(k)
                #k.sort()
                k = str(k)
                self.templates[k] = v
        except Exception as ex:
            raise TemplateNLGException('No templates loaded from %s -- %s!' %
                                       (file_name, ex))

    def get_generic_da(self, da, svs):
        """\
        Given a dialogue act and a list of slots and values, substitute
        the values with generic slot names.
        """
        # copy the instance
        da = copy.deepcopy(da)
        # find matching slots & values
        for name, value in svs:
            for dai in da:
                if dai.name == name and dai.value == value:
                    # there is match, make it generic
                    dai.value = '{%s}' % name
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
            rng = [1,]
        elif len(svs) == 2:
            rng = [1, 2, ]
        elif len(svs) == 3:
            rng = [1, 2, 3, ]
        else:
            rng = [1, 2, len(svs)-1, len(svs)]

        for r in rng:
            for cmb in itertools.combinations(svs, r):
                generic_da = self.get_generic_da(da, cmb)
                try:
                    tpl = self.random_select(self.templates[str(generic_da)])
                except KeyError:
                    continue
                return tpl

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
                           u"Welcome".
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
                raise TemplateNLGException("Unsupported generation type. "\
                 "At this level, the template cannot be a tuple: template = %s" % unicode(tpl))
        elif isinstance(tpl, list):
            raise TemplateNLGException("Unsupported generation type. "\
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
                tpl = self.random_select(self.match_generic_templates(da, svs))
            except TemplateNLGException:
                composed_tpl = []

                # try to find a template for each dialogue act item and concatenate them
                try:
                    dai_tpl = []
                    for dai in da:
                        try:
                            dai_tpl = self.random_select(self.templates[unicode(dai)])
                        except KeyError:
                            # try to find a relaxed match
                            dax = DialogueAct()
                            dax.append(dai)
                            svsx = dax.get_slots_and_values()
                            dai_tpl = self.random_select(self.match_generic_templates(dax, svsx))
                            dai_tpl = self.fill_in_template(dai_tpl, svsx)

                        composed_tpl.append(dai_tpl)

                    tpl = ' '.join(composed_tpl)

                except TemplateNLGException:
                    # nothing to do, I must backoff
                    tpl = self.backoff(da)

            self.last_utterance = self.fill_in_template(tpl, svs)

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

        if self.cfg['NLG']['Template']['model']:
            self.load_templates(self.cfg['NLG']['Template']['model'])

    def fill_in_template(self, tpl, svs):
        """\
        Simple text replacement template filling.
        """
        return tpl.format(**dict(svs))


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
