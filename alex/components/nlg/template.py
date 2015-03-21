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
from alex.components.dm.ontology import Ontology


class AbstractTemplateNLG(object):
    """\
    Base abstract class for template-filling generators, providing the
    routines for template loading and selection.

    The generation (i.e. template filling) is left to the derived classes.

    It implements numerous backoff strategies:
    1) it matches the exactly the input dialogue against the templates
    2) if it cannot find exact match, then it tries to find a generic template (slot-independent)
    3) if it cannot find a generic template, the it tries to compose
        the template from templates for individual dialogue act items
    """

    def __init__(self, cfg):
        """\
        Constructor, just save a link to the configuration.
        """
        self.cfg = cfg
        # this will save the last utterance
        self.last_utterance = u""
        # setup the composing strategy
        self.compose_utterance = self.compose_utterance_greedy
        self.compose_greedy_lookahead = 5
        if 'NLG' in self.cfg and 'TemplateCompose' in self.cfg['NLG']:
            compose_setting = \
                    self.cfg['NLG']['TemplateCompose'].tolower().strip()
            if compose_setting.startswith('greedy'):
                self.compose_utterance = self.compose_utterance_greedy
                self.compose_greedy_lookahead = \
                        int(re.search(r'\d+', compose_setting).group(0))
            elif compose_setting == 'single':
                self.compose_utterance = self.compose_utterance_single

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
        Find a matching template for a dialogue act using substitutions
        for slot values.

        Returns a matching template and a dialogue act where values of some
        of the slots are substituted with a generic value.
        """
        tpl = None
        # try to find increasingly generic templates
        # limit the complexity of the search
        if len(svs) == 0:
            rng = []
        elif len(svs) == 1:
            rng = [1]
        elif len(svs) == 2:
            rng = [1, 2]
        else:
            rng = [1, len(svs) - 1, len(svs)]

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
        (a tree-like structure).
        In the first level, the algorithm selects one of N.
        In the second level, for every item it selects one of M,
        and joins them together.
        This continues toward the leaves which must be non-list objects.

        There are the following random selection options (only the first
        three):

        (1)
            {
            'hello()' : u"Hello",
            }

            This will return the "Hello" string.

        (2)
            {
            'hello()' : (u"Hello",
                         u"Hi",
                        ),
            }

            This will return one of the "Hello" or "Hi" strings.


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

            This will return one of the following strings:
                "Hello. How are you doing? Speak!"
                "Hi. How are you doing? Speak!"
                "Hello. Welcome. Speak!"
                "Hi. Welcome. Speak!"
                "Hi my friend."
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
                raise TemplateNLGException("Unsupported generation type. " +
                                           "At this level, the template" +
                                           "cannot be a tuple: template = %s" %
                                           unicode(tpl))
        elif isinstance(tpl, list):
            raise TemplateNLGException("Unsupported generation type. " +
                                       "At this level, the template cannot " +
                                       "be a list: template = %s" %
                                       unicode(tpl))
        else:
            raise TemplateNLGException("Unsupported generation type.")

    def match_and_fill_generic(self, da, svs):
        """\
        Match a generic template and fill in the proper values for the slots
        which were substituted by a generic value.

        Will return the output text with the proper values filled in if a
        generic template can be found; will throw a TemplateNLGException
        otherwise.
        """
        # find a generic template
        tpls, mda = self.match_generic_templates(da, svs)
        tpl = self.random_select(tpls)
        svs_mda = mda.get_slots_and_values()

        # prepare a list of generic values to be filled in
        svsx = []
        for (slot_orig, val_orig), (_, val_generic) in zip(svs, svs_mda):

            if val_generic.startswith('{'):
                svsx.append([val_generic[1:-1], val_orig])
            else:
                svsx.append([slot_orig, val_orig])
        # return with generic values filled in
        return self.fill_in_template(tpl, svsx)

    def generate(self, da):
        """\
        Generate the natural text output for the given dialogue act.

        First, try to find an exact match with no variables to fill in.
        Then try to find a relaxed match of a more generic template and
        fill in the actual values of the variables.
        """
        utterance = ''
        try:
            if unicode(da) == 'irepeat()':
                # just return last utterance
                utterance = self.last_utterance
            else:
                # try to return exact match
                utterance = self.random_select(self.templates[unicode(da)])
        except KeyError:
            # try to find a relaxed match
            svs = da.get_slots_and_values()

            try:
                utterance = self.match_and_fill_generic(da, svs)

            except TemplateNLGException:
                # try to find a template for each dialogue act item and concatenate them
                try:
                    utterance = self.compose_utterance(da)

                except TemplateNLGException:
                    # nothing to do, I must backoff
                    utterance = self.backoff(da)

        if re.match(r'^(inform|i?confirm|request|hello)', unicode(da)):
            self.last_utterance = utterance
        return utterance

    def compose_utterance_single(self, da):
        """\
        Compose an utterance from templates for single dialogue act items.
        Returns the composed utterance.
        """
        composed_utt = []
        # try to find a template for each single dialogue act item
        for dai in da:
            try:
                # look for an exact match
                dai_utt = self.random_select(self.templates[unicode(dai)])
            except KeyError:
                # try to find a relaxed match
                dax = DialogueAct()
                dax.append(dai)
                svsx = dax.get_slots_and_values()
                try:
                    dai_utt = self.match_and_fill_generic(dax, svsx)
                except TemplateNLGException:
                    dai_utt = unicode(dai)

            composed_utt.append(dai_utt)
        return ' '.join(composed_utt)

    def compose_utterance_greedy(self, da):
        """\
        Compose an utterance from templates by iteratively looking for
        the longest (up to self.compose_greedy_lookahead) matching
        sub-utterance at the current position in the DA.

        Returns the composed utterance.
        """
        composed_utt = []
        sub_start = 0
        # pass through the dialogue act
        while sub_start < len(da):
            dax_utt = None
            dax_len = None
            # greedily look for the longest template that will cover the next
            # dialogue act items (try longer templates first, from maximum
            # length given in settings down to 1).
            for sub_len in xrange(self.compose_greedy_lookahead, 0, -1):
                dax = DialogueAct()
                dax.extend(da[sub_start:sub_start + sub_len])
                try:
                    # try to find an exact match
                    dax_utt = self.random_select(self.templates[unicode(dax)])
                    dax_len = sub_len
                    break
                except KeyError:
                    # try to find a relaxed match
                    svsx = dax.get_slots_and_values()
                    try:
                        dax_utt = self.match_and_fill_generic(dax, svsx)
                        dax_len = sub_len
                        break
                    except TemplateNLGException:
                        # nothing found: look for shorter templates
                        continue
            if dax_utt is None:  # dummy backoff
                dax_utt = unicode(da[sub_start])
                dax_len = 1
            composed_utt.append(dax_utt)
            sub_start += dax_len
        return ' '.join(composed_utt)

    def fill_in_template(self, tpl, svs):
        """\
        Fill in the given slot values of a dialogue act into the given
        template. This should be implemented in derived classes.
        """
        raise NotImplementedError()

    def backoff(self, da):
        """\
        Provide an alternative NLG template for the dialogue
        output which is not covered in the templates.
        This serves as a backoff solution.
        This should be implemented in derived classes.
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

        # load templates
        if 'model' in self.cfg['NLG']['Template']:
            self.load_templates(self.cfg['NLG']['Template']['model'])

        # load ontology
        self.ontology = Ontology()
        if 'ontology' in self.cfg['NLG']['Template']:
            self.ontology.load(cfg['NLG']['Template']['ontology'])

        # initialize pre- and post-processing
        self.preprocessing = None
        self.postprocessing = None
        if 'preprocessing_cls' in self.cfg['NLG']['Template']:
            self.preprocessing = self.cfg['NLG']['Template']['preprocessing_cls'](self.ontology)
        if 'postprocessing_cls' in self.cfg['NLG']['Template']:
            self.postprocessing = self.cfg['NLG']['Template']['postprocessing_cls']()

    def fill_in_template(self, tpl, svs):
        """\
        Simple text replacement template filling.

        Applies template NLG pre- and postprocessing, if applicable.
        """

        svs_dict = dict(svs)
        if self.preprocessing is not None:
            tpl, svs_dict = self.preprocessing.preprocess(tpl, svs_dict)

        out_text = tpl.format(**svs_dict)
        if self.postprocessing is not None:
            return self.postprocessing.postprocess(out_text)
        return out_text


class TemplateNLGPreprocessing(object):
    """Base class for template NLG preprocessing, handles preprocessing of the
    values to be filled into a template.

    This base class provides no functionality, it just defines an interface
    for derived language-specific and/or domain-specific classes.
    """

    def __init__(self, ontology):
        self.ontology = ontology

    def preprocess(self, svs_dict):
        raise NotImplementedError()


class TemplateNLGPostprocessing(object):
    """Base class for template NLG postprocessing, handles postprocessing of the
    text resulting from filling in a template.

    This base class provides no functionality, it just defines an interface
    for derived language-specific and/or domain-specific classes.
    """

    def __init__(self):
        pass

    def postprocess(self, nlg_text):
        raise NotImplementedError()


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
