#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

__all__ = ['da', 'dailrclassifier', 'daiklrclassifier', 'templateclassifier']

import copy
import sys
import os.path

from collections import defaultdict

from SDS.components.asr.utterance \
    import Utterance, UtteranceHyp, UtteranceNBList, UtteranceConfusionNetwork
from SDS.utils.text import split_by
from SDS.utils.exception import SDSException, DAILRException

import SDS.components.slu.da


database = None


class CategoryLabelDatabase:
    """ Provides a convenient interface to a database of slot value pairs aka
        category labels.
    """
    def __init__(self, file_name):
        self.database = {}
        self.synonym_value_category = []

        if file_name:
            self.load(file_name)

    def __iter__(self):
        for i in self.synonym_value_category:
            yield i

    def load(self, file_name):
        global database

        database = None
        execfile(file_name, globals())
        if database is None:
            raise Exception("No database loaded!")
        self.database = database

        self.normalise_database()
        self.gen_synonym_value_category()

    def normalise_database(self):
        """Normalise database. E.g. split utterances into sequences of words.
        """
        for name in self.database:
            for value in self.database[name]:
                for i, synonym in enumerate(self.database[name][value]):
                    new_synonym = synonym

                    new_synonym = new_synonym.split()
                    self.database[name][value][i] = new_synonym

    def gen_synonym_value_category(self):
        for name in self.database:
            for value in self.database[name]:
                for synonym in self.database[name][value]:
                    self.synonym_value_category.append((synonym, value, name))

        self.synonym_value_category.sort(
            key=lambda svc: len(svc[0]), reverse=True)


class SLUPreprocessing:
    """ Implements processing of utterances or utterances and dialogue acts.
    The main purpose is to replace all values in the database by its category
    labels (slot names) to reduce the complexity of the input utterances.

    In addition, it implements text normalisation for SLU input, e.g. removing
    filler words such as UHM, UM, etc. converting "I'm" into "I am", etc. Some
    normalisation is hard-coded. However, it can be updated by providing
    normalisation patterns.
    """
    def __init__(self, cldb, text_normalization=None):
        self.cldb = cldb

        if text_normalization:
            self.text_normalization_mapping = text_normalization
        else:
            self.text_normalization_mapping = [(['erm', ], []),
                                               (['uhm', ], []),
                                               (['um', ], []),
                                               (["i'm", ], ['i', 'am']),
                                               (['(sil)', ], []),
                                               (['(%hesitation)', ], []),
                                               (['(hesitation)', ], [])
                                               ]

    def text_normalisation(self, utterance):
        """ It normalises the input utterances (the output of an ASR engine).

        E.g., it removes filler words such as UHM, UM, etc., converts "I'm"
        into "I am", etc.
        """

        utterance.lower()

        for mapping in self.text_normalization_mapping:
            utterance.replace(mapping[0], mapping[1])

        return utterance

    def values2category_labels_in_utterance(self, utterance):
        """Replaces all strings matching values in the database by their slot
        names. Since multiple slots can have the same values, the algorithm
        produces multiple outputs.

        Returns a list of utterances with replaced database values, and
        provides a dictionary with mapping between category labels and the
        original string.

        """
        utterance = copy.deepcopy(utterance)

        # (FIXME: Why not just use collections.Counter?)
        category_label_counter = defaultdict(int)
        category_labels = {}

        for slot, value, surface in self.cldb:
            # XXX Utterance consists of words (surface forms), not slots!
            # Right?
            if slot in utterance:
                # XXX So the mapping is _from surface forms_ _to category
                # labels_!? The method docstring would not suggest this.
                category_label = '{cat}-{idx!slot}'.format(
                    cat=surface.upper(),
                    idx=category_label_counter[surface.upper()])
                category_label_counter[surface.upper()] += 1

                category_labels[category_label] = (value, slot)
                # Assumes the surface strings don't overlap.
                # FIXME: Perhaps replace all instead of just the first one.
                utterance.replace(slot, [category_label])

                break

        return utterance, category_labels

    def values2category_labels_in_da(self, utterance, da):
        """ Replaces all strings matching values in the database by their slot
        names. Since multiple slots can have the same values, the algorithm can
        produce multiple outputs.

        Returns a list of utterances with replaced database values, and
        provides a dictionary with mapping between category labels and the
        original string.

        """
        da = copy.deepcopy(da)
        utterance = copy.deepcopy(utterance)

        utterance, category_labels = self.values2category_labels_in_utterance(
            utterance)

        for cl in category_labels:
            for dai in da:
                if dai.value == category_labels[cl][0]:
                    dai.value = cl
                    break

        return utterance, da, category_labels

    def category_labels2values_in_utterance(self, utterance, category_labels):
        """Reverts the result of the values2category_labels_in_utterance(...)
        function.

        Returns the original utterance.
        """
        utterance = copy.deepcopy(utterance)

        for cl in category_labels:
            utterance.replace([cl, ], category_labels[cl][1])

        return utterance

    def category_labels2values_in_da(self, da, category_labels):
        """Reverts the result of the values2category_labels_in_da(...)
        function.

        Returns the original dialogue act.
        """
        da = copy.deepcopy(da)
        for dai in da.dais:
            if dai.value in category_labels:
                dai.value = category_labels[dai.value][0]

        return da

    def category_labels2values_in_nblist(self, nblist, category_labels):
        """Reverts the result of the values2category_labels_in_da(...)
        function.

        Returns the converted N-best list.
        """
        nblist = copy.deepcopy(nblist)
        for prob, dai in nblist.n_best:
            for dai in da:
                if dai.value in category_labels:
                    dai.value = category_labels[dai.value][0]

        return nblist

    def category_labels2values_in_confnet(self, confnet, category_labels):
        """Reverts the result of the values2category_labels_in_da(...)
        function.

        Returns the converted confusion network.
        """
        confnet = copy.deepcopy(confnet)

        for prob, dai in confnet.cn:
            if dai.value in category_labels:
                dai.value = category_labels[dai.value][0]

        return confnet


class SLUInterface:
    """ Defines a prototypical interface each parser should provide for
        parsing.

    It should be able to parse:
      1) a utterance hypothesis (an instance of UtteranceHyp)
          - output: SLUHypothesis sub-class

      2) a N-best list of utterances (an instance of UtteranceNBList)
          - output: SLUHypothesis sub-class

      3) a confusion network (an instance of UtteranceConfusionNetwork)
          - output: SLUHypothesis sub-class
    """

    def parse_1_best(self, utterance):
        raise SLUException("Not implemented")

    def parse_nblist(self, utterance_list):
        raise SLUException("Not implemented")

    def parse_confnet(self, confnet):
        raise SLUException("Not implemented")

    def parse(self, utterance, *args, **kw):
        """Check what the input is and parse accordingly."""

        if isinstance(utterance, Utterance):
            return self.parse_1_best(utterance, *args, **kw)

        elif isinstance(utterance, UtteranceHyp):
            return self.parse_1_best(utterance, *args, **kw)

        elif isinstance(utterance, UtteranceNBList):
            return self.parse_nblist(utterance, *args, **kw)

        elif isinstance(utterance, UtteranceConfusionNetwork):
            return self.parse_confnet(utterance, *args, **kw)

        else:
            raise DAILRException("Unsupported input in the SLU component.")
