#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

if __name__ == "__main__":
    import autopath
import __init__

from alex.components.slu.da import DialogueAct
from alex.components.nlg.template import TemplateNLG
from alex.utils.config import Config, as_project_path

CONFIG_DICT = {
    'NLG': {
        'debug': True,
        'type': 'Template',
        'Template' : {
            'model': as_project_path('applications/PublicTransportInfoCS/nlg_templates.cfg')
        },
    }
}

class TestTemplateNLG(unittest.TestCase):
    def setUp(self):
        self.cfg = Config.load_configs(config=CONFIG_DICT, use_default=False,
                                       log=False)

    def test_template_nlg(self):

        cfg = self.cfg
        nlg = TemplateNLG(cfg)

        da = DialogueAct('affirm()&inform(num_transfers="2")').sort()
        correct_text = u"Ano. Na dané trase jsou dva přestupy."
        generated_text = nlg.generate(da)

        s = []
        s.append("")
        s.append("Input DA:")
        s.append(unicode(da))
        s.append("")
        s.append("Correct text:")
        s.append(unicode(correct_text))
        s.append("")
        s.append("Generated text:")
        s.append(unicode(generated_text))
        s.append("")

        self.assertEqual(unicode(correct_text), unicode(generated_text))

    def test_template_nlg_r(self):

        cfg = self.cfg
        nlg = TemplateNLG(cfg)

        da = DialogueAct('affirm()&inform(from_stop=Sparta)').sort()
        correct_text = "Ano, jede to ze zastávky Sparta."
        generated_text = nlg.generate(da)

        s = []
        s.append("")
        s.append("Input DA:")
        s.append(unicode(da))
        s.append("")
        s.append("Correct text:")
        s.append(unicode(correct_text))
        s.append("")
        s.append("Generated text:")
        s.append(unicode(generated_text))
        s.append("")

        self.assertEqual(unicode(correct_text), unicode(generated_text))

if __name__ == '__main__':
    unittest.main()
