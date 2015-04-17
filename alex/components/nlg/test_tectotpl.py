#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import unittest

if __name__ == "__main__":
    import autopath
import __init__

from alex.components.slu.da import DialogueAct
from alex.components.nlg.template import TectoTemplateNLG
from alex.utils.config import Config, as_project_path

CONFIG_DICT = {
    'NLG': {
        'debug': True,
        'type': 'TectoTemplate',
        'TectoTemplate': {
            'model': as_project_path('applications/TectoTplTest/nlgtemplates.cfg'),
            'scenario': [
                {'block': 'read.TectoTemplates', 'args': {'encoding': None}},
                {'block': 't2a.CopyTTree'},
                {'block': 't2a.cs.ReverseNumberNounDependency'},
                {'block': 't2a.cs.InitMorphcat'},
                {'block': 't2a.cs.GeneratePossessiveAdjectives'},
                {'block': 't2a.cs.MarkSubject'},
                {'block': 't2a.cs.ImposePronZAgr'},
                {'block': 't2a.cs.ImposeRelPronAgr'},
                {'block': 't2a.cs.ImposeSubjPredAgr'},
                {'block': 't2a.cs.ImposeAttrAgr'},
                {'block': 't2a.cs.ImposeComplAgr'},
                {'block': 't2a.cs.DropSubjPersProns'},
                {'block': 't2a.cs.AddPrepositions'},
                {'block': 't2a.cs.AddSubconjs'},
                {'block': 't2a.cs.GenerateWordForms', 'args': {'model': 'flect/model-t253-l1_10_00001-alex.pickle.gz'}},
                {'block': 't2a.cs.VocalizePrepos'},
                {'block': 't2a.cs.CapitalizeSentStart'},
                {'block': 'a2w.cs.ConcatenateTokens'},
                {'block': 'a2w.cs.RemoveRepeatedTokens'},
            ],
            'global_args': {'language': 'cs', 'selector': ''},
            'data_dir': as_project_path('applications/TectoTplTest/data/'),
        },
    }
}


DAS = ['affirm()&inform(task="find")&inform(pricerange="levný")',
       'affirm()&inform(task="find")&inform(food="čínský")&inform(pricerange="levný")']

TEXTS = ['Dobře, takže hledáte něco levného.',
         'Dobře, takže hledáte nějaký levný podnik s čínským jídlem.']


class TestTectoTemplateNLG(unittest.TestCase):

    def test_tecto_template_nlg(self):
        # initialize
        cfg = Config.load_configs(config=CONFIG_DICT, use_default=False,
                                  log=False)
        nlg = TectoTemplateNLG(cfg)
        # test all cases
        for da, correct_text in zip(DAS, TEXTS):
            # try generation
            da = DialogueAct(da)
            generated_text = nlg.generate(da)
            # print output
            s = []
            s.append("")
            s.append("Input DA:")
            s.append(unicode(da))
            s.append("")
            s.append("Correct text:")
            s.append(correct_text)
            s.append("")
            s.append("Generated text:")
            s.append(generated_text)
            s.append("")

            # test the result
            self.assertEqual(correct_text, generated_text)


if __name__ == '__main__':
    unittest.main()
