#!/usr/bin/env python
# -*- coding: utf-8 -*-

from SDS.components.slu import SLUPreprocessing, load_utterances, load_das

utterances_dict = load_utterances('./resources/towninfo-train.trn')
semantics_dict = load_das('./resources/towninfo-train.sem')

# load the database definition
execfile('./resources/database.py')

slu_prep = SLUPreprocessing(database)

for k in semantics_dict:
  print '='*120
  print utterances_dict[k]
  print semantics_dict[k]
  
  utterance, da, category_labels = slu_prep.values2slot_names_in_da(utterances_dict[k], 
                                                                    semantics_dict[k])
  
  print '-'*120
  print utterance
  print da
  print category_labels
  print '-'*120


  full_utterance = slu_prep.slot_names2values_in_utterance(utterance, category_labels)
  full_da = slu_prep.slot_names2values_in_da(da, category_labels)
  
  print full_utterance
  print full_da
  
