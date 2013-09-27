#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
The original FJ's implementation of SLU base classes.
"""

from collections import defaultdict
import copy

from alex.utils.config import load_as_module


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
        db_mod = load_as_module(file_name, force=True)
        if not hasattr(db_mod, 'database'):
            from exception import SLUException
            raise SLUException("The category label database does not define "
                               "the `database' object!")
        self.database = db_mod.database

        self.normalise_database()
        self.gen_synonym_value_category()

    def normalise_database(self):
        """Normalise database. E.g. split utterances into sequences of words.
        """
        for name in self.database:
            for value in self.database[name]:
                for form_idx, form in enumerate(self.database[name][value]):
                    self.database[name][value][form_idx] = form.split()

    def gen_synonym_value_category(self):
        for name in self.database:
            for value in self.database[name]:
                for synonym in self.database[name][value]:
                    self.synonym_value_category.append((synonym, value, name))

        self.synonym_value_category.sort(
            key=lambda svc: len(svc[0]), reverse=True)


class SLUPreprocessing(object):
    """Implements processing of utterances or utterances and dialogue acts.
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
            utterance = utterance.replace(mapping[0], mapping[1])
        return utterance

    def values2category_labels_in_utterance(self, utterance):
        """Replaces strings matching surface forms in the label database with
        their slot names plus index.  Since multiple slots can have the same
        surface forms, the return value, in general, may comprise of multiple
        alternatives.

        Arguments:
            utterance -- a list of (surface, value, slot) tuples comprising the
                         utterance

        Returns a list of utterances with replaced database values, and
        a dictionary with mapping from category labels to the original
        strings.

        """
        utterance = copy.deepcopy(utterance)

        category_label_counter = defaultdict(int)
        category_labels = {}

        for surface, value, slot in self.cldb:
            slot_upper = slot.upper()
            if surface in utterance:
                category_label = u'{cat}-{idx}'.format(
                    cat=slot_upper,
                    idx=category_label_counter[slot_upper])
                category_label_counter[slot_upper] += 1

                category_labels[category_label] = (value, surface)
                # Assumes the surface strings don't overlap.
                # FIXME: Perhaps replace all instead of just the first one.
                utterance = utterance.replace(surface, [category_label])
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
            # FIXME: Use a new method, category_label2phrase, which will know
            # that the new value is not an abstraction for the original one.
            utterance = utterance.phrase2category_label(
                [cl, ], category_labels[cl][1])

        return utterance

    def category_labels2values_in_da(self, da, category_labels):
        """Reverts the result of the values2category_labels_in_da(...)
        function.

        Returns the original dialogue act.
        """
        da = copy.deepcopy(da)
        for dai in da.dais:
            dai.category_label2value(category_labels)
            # if dai.value in category_labels:
                # dai.value = category_labels[dai.value][0]
        return da

    def category_labels2values_in_nblist(self, nblist, category_labels):
        """Reverts the result of the values2category_labels_in_da(...)
        function.

        Returns the converted N-best list.
        """
        nblist = copy.deepcopy(nblist)
        for _, da in nblist.n_best:
            for dai in da:
                dai.category_label2value(category_labels)
        return nblist

    def category_labels2values_in_confnet(self, confnet, category_labels):
        """Reverts the result of the values2category_labels_in_da(...)
        function.

        Returns the converted confusion network.
        """
        confnet = copy.deepcopy(confnet)
        for _, dai in confnet.cn:
            dai.category_label2value(category_labels)
        # XXX A quick hack.
        # DAIs that did not get substituted are almost surely wrong. Remove
        # them.
        new_cn = [(prob, dai) for (prob, dai) in confnet.cn
                  if not dai.value or '-' not in dai.value]
        # XXX This may break the correct behaviour of the Confnet class...
        confnet.cn = new_cn

        return confnet
