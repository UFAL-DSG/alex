#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import unittest

if __name__ == "__main__":
    import autopath

from alex.components.asr.utterance import UtteranceConfusionNetwork
from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.common import slu_factory
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, \
    DialogueActConfusionNetwork, merge_slu_nblists, merge_slu_confnets
import alex.components.slu.dailrclassifier_mk as DAILRSLU
from alex.utils.config import Config
from alex.utils.config import as_project_path

CONFIG_DICT = {
  'SLU': {
    'debug': True,
    'type': 'cl-tracing',
    'cl-tracing': {
        'cldb_fname': as_project_path(os.path.join(
            'applications', 'CamInfoRest', 'data', 'database.py')),
        'do_preprocessing': True,
        'testing': {
            'model_fname': as_project_path(os.path.join(
                'applications', 'CamInfoRest', 'models',
                '130516_minf60-minfc35-mind60.slu_model.gz')),
            'renormalise': True,   # Whether to normalise probabilities for
                                   # alternative values for same slots.
            'threshold': None,     # set to None to use the learned one
            'vanilla': True,       # set to True if no output files should be
                                   # written
        }
    }
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
        # asr_confnet.normalise()
        asr_confnet.sort()

        slu_best_da = DialogueAct("inform(=restaurant)&inform(food=chinese)")

        cfg = Config.load_configs(config=CONFIG_DICT, use_default=False,
                                  log=False)
        # cldb = CategoryLabelDatabase(cfg['SLU']['cldb'])
        # preprocessing = SLUPreprocessing(cldb)
        # slu = DAILRSLU.DAILogRegClassifier(preprocessing)
        # slu.load_model(cfg['SLU']['DAILogRegClassifier']['model'])
        slu = slu_factory(cfg, require_model=True)
        slu_hyp = slu.parse({'utt_cn': asr_confnet})
        slu_hyp_best_da = slu_hyp.get_best_da().sort()

        s = []
        s.append("")
        s.append("ASR confnet:")
        s.append(unicode(asr_confnet))
        s.append("")
        s.append("Correct Best SLU dialogue act:")
        s.append(unicode(slu_best_da))
        s.append("")
        s.append("SLU confnet:")
        s.append(unicode(slu_hyp))
        s.append("")
        s.append("Best SLU dialogue act:")
        s.append(unicode(slu_hyp_best_da))
        s.append("")
        print '\n'.join(s)

        self.assertEqual(unicode(slu_best_da), unicode(slu_hyp_best_da))

if __name__ == '__main__':
    unittest.main()
