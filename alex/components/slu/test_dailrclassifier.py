#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

if __name__ == "__main__":
    import autopath
import __init__

from alex.components.asr.utterance import UtteranceConfusionNetwork
from alex.components.slu import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, \
    DialogueActConfusionNetwork, merge_slu_nblists, merge_slu_confnets
import alex.components.slu.dailrclassifier as DAILRSLU
from alex.utils.config import Config
from alex.utils.config import as_project_path


CONFIG_DICT = {
  'SLU': {
    'debug': True,
    'cldb': as_project_path("applications/CamInfoRest/data/database.py"),
    'type': 'DAILogRegClassifier',
    'DAILogRegClassifier': {
        # 'model': as_project_path('applications/CamInfoRest/slu-lr-trn.model'),
        'model':
        as_project_path('applications/CamInfoRest/models/130404_top1000-minf15-minfc10-mind15-nocal-s0.1.slu_model')
    },
  }
}


class TestDAILRClassifier(unittest.TestCase):
    def test_confnet_parsing(self):

        A1, A2, A3 = 0.90, 0.05, 0.05
        B1, B2, B3 = 0.70, 0.20, 0.10
        C1, C2, C3 = 0.80, 0.10, 0.10

        asr_confnet = UtteranceConfusionNetwork()
        asr_confnet.add([[A1, "want"], [A2, "has"], [A3, 'ehm']])
        asr_confnet.add([[B1, "Chinese"],  [B2, "English"], [B3, 'cheap']])
        asr_confnet.add([[C1, "restaurant"],  [C2, "pub"],   [C3, 'hotel']])
        asr_confnet.merge()
        asr_confnet.normalise()
        asr_confnet.sort()

        slu_best_da = DialogueAct("inform(=restaurant)&inform(food=chinese)")

        cfg = Config(config=CONFIG_DICT)
        cldb = CategoryLabelDatabase(cfg['SLU']['cldb'])
        preprocessing = SLUPreprocessing(cldb)
        slu = DAILRSLU.DAILogRegClassifier(preprocessing)
        slu.load_model(cfg['SLU']['DAILogRegClassifier']['model'])
        slu_hyp = slu.parse(asr_confnet)
        slu_hyp_best_da = slu_hyp.get_best_da().sort()

        s = []
        s.append("")
        s.append("ASR confnet:")
        s.append(str(asr_confnet))
        s.append("")
        s.append("Correct Best SLU dialogue act:")
        s.append(str(slu_best_da))
        s.append("")
        s.append("SLU confnet:")
        s.append(str(slu_hyp))
        s.append("")
        s.append("Best SLU dialogue act:")
        s.append(str(slu_hyp_best_da))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(str(slu_best_da), str(slu_hyp_best_da))

if __name__ == '__main__':
    unittest.main()
