#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

if __name__ == "__main__":
    import autopath


from alex.components.slu.base import CategoryLabelDatabase
from alex.components.slu.dailrclassifier import DAILogRegClassifier
from alex.components.asr.utterance import Utterance

from aotb_preprocessing import AOTBSLUPreprocessing

cldb = CategoryLabelDatabase('./data/database.py')
pp = AOTBSLUPreprocessing(cldb)
pp.text_normalization_mapping += [
    (["ve"], ["v"]),
]

lr_classifier = DAILogRegClassifier(pp)
lr_classifier.load_model('./slu-lr-trn.model')

while 1:
    utt = Utterance(raw_input().decode('utf8'))
    obs = {'utt': utt}
    print lr_classifier.parse(obs, verbose=2)
