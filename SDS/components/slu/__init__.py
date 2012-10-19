#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['da','dailrclassifier','daiklrclassifier', 'templateclassifier']

import copy

from collections import defaultdict

from SDS.utils.string import split_by
from SDS.utils.exception import SDSException

import SDS.components.slu.da

class CategoryLabelDatabase:
  """ Provides a convenient interface to a database of slot value pairs aka category labels.
  """
  def __init__(self, file_name):
    self.database = {}
    self.synonym_value_catogery = []

    if file_name:
      self.load(file_name)

  def __iter__(self):
    for i in self.synonym_value_catogery:
      yield i

  def load(self, file_name):
    execfile(file_name, globals())
    self.database = database

    self.normalise_database()
    self.gen_synonym_value_catogery()

  def normalise_database(self):
    """normalise database. E.g. split utterances into sequences of words.
    """
    for name in self.database:
      for value in self.database[name]:
        for i, synonym in enumerate(self.database[name][value]):
          new_synonym = synonym

          new_synonym = new_synonym.split()
          self.database[name][value][i] = new_synonym

  def gen_synonym_value_catogery(self):
    for name in self.database:
      for value in self.database[name]:
        for synonym in self.database[name][value]:
          self.synonym_value_catogery.append((synonym,  value, name))


    self.synonym_value_catogery.sort(key = lambda svc: len(svc[0]), reverse=True)

class SLUPreprocessing:
  """ Implements precessing of utterances or utterances and dialogue acts. The main purpose is to replace
  all values in the database by its category labels (slot names) to reduce the complexity of the input
  utterances.

  In addition, it implements text normalisation for SLU input, e.g. removing filler words such as
  UHM, UM, etc. converting "I'm" into "I am", etc. Some normalisation is hard coded. However,
  it can be updated by providing normalisation patterns.
  """

  def __init__(self, cldb, text_normalization = None):
    self.cldb = cldb

    if text_normalization:
      self.text_normalization_mapping = text_normalization
    else:
      self.text_normalization_mapping = [(['erm', ], []),
                                        (['uhm', ], []),
                                        (['um', ], []),
                                        (["I'm", ], ['I', 'am']),
                                        (['(sil)', ], []),
                                        (['(%hesitation)', ], []),
                                        (['(hesitation)', ], [])
                                        ]



  def text_normalization(self, utterance):
    """ It normalise the input utterances (the output of an ASR engine).

    E.g. removing filler words such as UHM, UM, etc. converting "I'm" into "I am", etc.
    """

    for mapping in self.text_normalization_mapping:
      utterance = utterance.replace(mapping[0], mapping[1])

    return utterance

  def values2category_labels_in_utterance(self, utterance):
    """ Replaces all strings matching values in the database by its slot names. Since multiple slots can have
    the same values, the algorithm produces multiple outputs.

    Returns a list of utterances with replaced database values. And it provides a dictionary with mapping
    between category labels and the original string.

    """

    utterance = copy.deepcopy(utterance)

    catgeory_label_counter = defaultdict(int)
    category_labels = {}

    for s, value, name in self.cldb:
      if s in utterance:
        category_label = name.upper()+'-'+str(catgeory_label_counter[name.upper()])
        catgeory_label_counter[name.upper()] +=1

        category_labels[category_label] = (value, s)
        utterance.replace(s, [category_label, ])

        break

    return utterance, category_labels

  def values2category_labels_in_da(self, utterance, da):
    """ Replaces all strings matching values in the database by its slot names. Since multiple slots can have
    the same values, the algorithm can produce multiple outputs.

    Returns a list of utterances with replaced database values. And it provides a dictionary with mapping
    between category labels and the original string.

    """

    da = copy.deepcopy(da)
    utterance = copy.deepcopy(utterance)

    utterance, category_labels = self.values2category_labels_in_utterance(utterance)

    for cl in category_labels:
      for dai in da:
        if dai.value == category_labels[cl][0]:
          dai.value = cl
          break

    return utterance, da, category_labels

  def category_labels2values_in_utterance(self, utterance, category_labels):
    """Reverts the result of the values2category_labels_in_utterance(...) function.

    Returns the original utterance.
    """

    utterance = copy.deepcopy(utterance)

    for cl in category_labels:
      utterance.replace([cl, ], category_labels[cl][1])

    return utterance

  def category_labels2values_in_da(self, da, category_labels):
    """Reverts the result of the values2category_labels_in_da(...) function.

    Returns the original dialogue act.
    """
    da = copy.deepcopy(da)
    for dai in da.dais:
      if dai.value in category_labels:
        dai.value = category_labels[dai.value][0]

    return da

class SLUInterface:
  """ Defines a prototypical interface each parser should provide for parsing.

  It should be able to parse:
    1) a single utterance (an instance of Utterance)
        - output: best interpretation and its confidence score (a tuple)
    2) a N-best list of utterances (an instance of UtteranceNBList)
        - output: N-best list of dialogue acts and their confidence scores
    3) a confusion network (an instance of UtteranceConfusionNetwork)
        - output: confusion network of dialogue acts
  """

  def parse(self, utterance):
    pass

  def parse_N_best_list(self, hyp_list):
    sluHyp = []
    #sluHyp = ["dialogue act", 0.X]*N
    return sluHyp

  def parse_confusion_network(self, conf_net):
    pass