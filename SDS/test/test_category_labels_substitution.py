#!/usr/bin/env python
# -*- coding: utf-8 -*-

import __init__

from SDS.components.asr.utterance import load_utterances
from SDS.components.slu.da import load_das
from SDS.components.slu import SLUPreprocessing

utterances_dict = load_utterances('./resources/towninfo-train.trn')
semantics_dict = load_das('./resources/towninfo-train.sem')

# load the database definition
execfile('./resources/database.py')

slu_prep = SLUPreprocessing(database)

for k in semantics_dict:
  print '='*120
  print utterances_dict[k]
  print semantics_dict[k]

  utterance, da, category_labels = slu_prep.values2category_labels_in_da(utterances_dict[k], semantics_dict[k])

  print '-'*120
  print utterance
  print da
  print category_labels
  print '-'*120


  full_utterance = slu_prep.category_labels2values_in_utterance(utterance, category_labels)
  full_da = slu_prep.category_labels2values_in_da(da, category_labels)

  print full_utterance
  print full_da

