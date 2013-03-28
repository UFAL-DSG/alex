#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import itertools
import copy

from alex.components.slu.da import DialogueAct
from alex.utils.exception import TemplateNLGException
from dummynlg import DummyNLG
from alex.utils.config import load_as_module
from alex.components.nlg.tectotpl.core.run import Scenario


class AbstractTemplateNLG(object):
    """\
    Base abstract class for template-filling generators, providing the
    routines for template loading and selection.

    The generation (i.e. template filling) is left to the derived classes.
    """

    def __init__(self, cfg):
        """\
        Constructor, just save a link to the configuration.
        """
        self.cfg = cfg

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
                k.sort()
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
        for r in range(1, len(svs) + 1):
            for cmb in itertools.combinations(svs, r):
                generic_da = self.get_generic_da(da, cmb)
                try:
                    tpl = self.random_select(self.templates[str(generic_da)])
                except KeyError:
                    continue
                return tpl
        # did not find anything
        raise TemplateNLGException("No match with generic templates.")

    def random_select(self, tmp):
        """\
        Randomly select alternative templates for generation.
        """
        if isinstance(tmp, list):
            return random.choice(tmp)
        elif isinstance(tmp, str):
            return tmp
        else:
            TemplateNLGException("Unsupported generation type.")

    def generate(self, da):
        """\
        Generate the natural text output for the given dialogue act.

        First, try to find an exact match with no variables to fill in.
        Then try to find a relaxed match of a more generic template and
        fill in the actual values of the variables.
        """
        da.sort()
        try:
            # try to return exact match
            return self.random_select(self.templates[str(da)])
        except KeyError:
            # try to find a relaxed match
            svs = da.get_slots_and_values()
            tpl = self.random_select(self.match_generic_templates(da, svs))
            return self.fill_in_template(tpl, svs)

    def fill_in_template(self, tpl, svs):
        """\
        Fill in the given slot values of a dialogue act into the given
        template. This should be implemented in derived classes.
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

        # if there is no match in the templates, back off to DummyNLG
        self.backoff_nlg = DummyNLG(cfg)

    def fill_in_template(self, tpl, svs):
        """\
        Simple text replacement template filling.
        """
        return tpl.format(**dict(svs))

    def generate(self, da):
        """\
        Try the normal template generation process and use back-off NLG if
        no template was found.
        """
        try:
            return super(TemplateNLG, self).generate(da)
        except TemplateNLGException:
            # no template was found, use back-off
            return self.backoff_nlg.generate(da)


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
        if not 'model' in self.cfg or not 'scenario' in self.cfg or \
                not 'data_dir' in self.cfg:
            raise TemplateNLGException('NLG scenario, data directory ' +
                                            'and templates must be defined!')
        # load templates
        self.load_templates(cfg['NLG']['TectoTemplate']['model'])
        # load NLG system
        self.nlg_rules = Scenario(cfg['NLG']['TectoTemplate'])
        self.nlg_rules.load_blocks()

    def fill_in_template(self, tpl, svs):
        """\
        Filling in tecto-templates, i.e. filling-in strings to templates
        and using rules to generate the result.
        """
        filled_tpl = tpl.format(**dict(svs))
        return self.nlg_rules.apply_to(filled_tpl)
