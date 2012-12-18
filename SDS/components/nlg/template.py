#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import itertools
import copy

from SDS.components.slu.da import DialogueAct
from SDS.utils.exception import TemplateNLGException
from dummynlg import DummyNLG

templates = None


class TemplateNLG:
    def __init__(self, cfg):
        self.cfg = cfg

        if self.cfg['NLG']['Template']['model']:
            self.load(self.cfg['NLG']['Template']['model'])

        # if there is no match in the templates, back off to DummyNLG
        self.backoff_nlg = DummyNLG(cfg)

    def load(self, file_name):
        """FIXME: Executing external files is not ideal!
           It should be changed in the future!
        """
        global templates
        templates = None

        execfile(file_name, globals())
        if templates is None:
            raise Exception("No templates has been loaded!")

        # normalise the templates
        self.templates = {}
        for k, v in templates.iteritems():
            k = DialogueAct(k)
#            print "-"*120
#            print k, v
            k.sort()
            k = str(k)
#            print k, v
            self.templates[k] = v

    def get_generic_da(self, da, svs):
        """Substitute slot values with generic names."""
        da = copy.deepcopy(da)

        for name, value in svs:
            for dai in da:
                if dai.name == name and dai.value == value:
                    # there is match, make it generic
                    dai.value = '{%s}' % name

        return da

    def match_generic_templates(self, da):
        """\
        Find a matching template for a dialogue act
        using substitutions in case of the slot values.
        """
        text = None

        svs = da.get_slots_and_values()

        for r in range(1, len(svs) + 1):
            for cmb in itertools.combinations(svs, r):
                generic_da = self.get_generic_da(da, cmb)

                try:
                    text = self.random_select(self.templates[str(generic_da)])
                except KeyError:
                    continue

                c = dict(svs)
                text = text.format(**c)

                return text

        raise TemplateNLGException("No match with generic templates.")

    def random_select(self, tmp):
        """Randomly select text alternative for generation."""

        if isinstance(tmp, list):
            return random.choice(tmp)
        elif isinstance(tmp, str):
            return tmp
        else:
            TemplateNLGException("Unsupported generation type.")

    def generate(self, da):
        """Generate the natural text output for the given dialogue act."""

        da.sort()

        try:
            # try to return exact match
            return self.random_select(self.templates[str(da)])
        except KeyError:
            try:
                # try to find a relaxed match
                return self.random_select(self.match_generic_templates(da))
            except TemplateNLGException:
                # nothing was found
                return self.backoff_nlg.generate(da)
                #self.cfg['Logging']['system_logger'].warning("TemplateNLG: There is no matching template for %s" % da)
                #return self.random_select(self.templates[str('notemplate()')])

