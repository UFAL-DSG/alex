#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

__all__ = ['da', 'dailrclassifier', 'daiklrclassifier', 'templateclassifier']

import copy

from collections import defaultdict

from alex.components.asr.utterance \
    import Utterance, UtteranceHyp, UtteranceNBList, UtteranceConfusionNetwork
from alex.utils.config import load_as_module
from alex.utils.exception import SLUException, DAILRException


database = None


class CategoryLabelDatabase(object):
    """Provides a convenient interface to a database of slot value pairs aka
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

        db_mod = load_as_module(file_name, force=True)
        if not hasattr(db_mod, 'database'):
            raise Exception("No database loaded!")
        self.database = db_mod.database

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


class SLUPreprocessing(object):
    """Implements preprocessing of utterances or utterances and dialogue acts.
    The main purpose is to replace all values in the database by their category
    labels (slot names) to reduce the complexity of the input utterances.

    In addition, it implements text normalisation for SLU input, e.g. removing
    filler words such as UHM, UM etc., converting "I'm" into "I am" etc.  Some
    normalisation is hard-coded. However, it can be updated by providing
    normalisation patterns.

    """
    def __init__(self, cldb, text_normalization=None):
        """Initialises a SLUPreprocessing object with particular preprocessing
        parameters.

        Arguments:
            cldb -- an iterable of (surface, value, slot) tuples describing the
                    relation between surface forms and (slot, value) pairs
            text_normalization -- an iterable of tuples (source, target) where
                    `source' occurrences in the text should be substituted by
                    `target', both `source' and `target' being specified as
                    a sequence of words

        """
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
        """Replaces strings matching surface forms in the label database with
        their slot names plus index.

        NOT IMPLEMENTED YET:
        Since multiple slots can have the same surface forms, the return value,
        in general, may comprise of multiple alternatives.

        Arguments:
            utterance -- an instance of the Utterance class where the
                         substitutions should be done

        Returns an utterance with replaced database values, and a dictionary
        with mapping from category labels to the original strings.

        """
        utterance = copy.deepcopy(utterance)

        category_label_counter = defaultdict(int)
        slotval_for_cl = {}

        for surface, value, slot in self.cldb:
            slot_upper = slot.upper()
            if surface in utterance:
                category_label = '{cat}-{idx}'.format(
                    cat=slot_upper,
                    idx=category_label_counter[slot_upper])
                category_label_counter[slot_upper] += 1

                slotval_for_cl[category_label] = (value, surface)
                # Assumes the surface strings don't overlap.
                # FIXME: Perhaps replace all instead of just the first one.
                utterance.replace(surface, [category_label])

                break

        return utterance, slotval_for_cl

    def values2category_labels_in_da(self, utterance, da):
        """Replaces strings matching surface forms in the label database with
        their slot names plus index both in `utterance' and `da' in
        a consistent fashion.

        NOT IMPLEMENTED YET:
        Since multiple slots can have the same surface forms, the return value,
        in general, may comprise of multiple alternatives.

        Arguments:
            utterance -- an instance of Utterance where the substitutions
                         should be done
            da -- an instance of DialogueAct where the substitutions should be
                  done

        Returns an utterance with replaced database values, the DA with
        replaced database values, and a dictionary with mapping from category
        labels to the original strings.

        """
        da = copy.deepcopy(da)
        utterance = copy.deepcopy(utterance)

        utterance, slotval_for_cl = self.values2category_labels_in_utterance(
            utterance)

        for cl in slotval_for_cl:
            for dai in da:
                # FIXME? Shouldn't other category labels with the same (slot,
                # value) be taken sometimes (i.e., should we sometimes use
                # also something like 'FOOD-1' if both 'FOOD-0' and 'FOOD-1'
                # are present)?
                if dai.value == slotval_for_cl[cl][0]:
                    dai.value = cl
                    break

        return utterance, da, slotval_for_cl

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
        # XXX The following line went like this:
        # for prob, dai in nblist.n_best:
        # but `da' was undefined below. Check that the following correction
        # works.
        for prob, da in nblist.n_best:
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


class SLUInterface(object):
    """Defines a prototypical interface each parser should provide for parsing.

    It should be able to parse:
      1) an utterance hypothesis (an instance of UtteranceHyp)
          - output: SLUHypothesis sub-class

      2) an N-best list of utterances (an instance of UtteranceNBList)
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
