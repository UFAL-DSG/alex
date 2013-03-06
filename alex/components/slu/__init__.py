#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

__all__ = ['da', 'dailrclassifier', 'daiklrclassifier', 'templateclassifier']

import copy

from collections import defaultdict
from itertools import product

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
        # Bookkeeping.
        self._form_val_upname = None
        self._form_upnames_vals = None

    def __iter__(self):
        """Yields tuples (form, value, name) from the database."""
        for tup in self.synonym_value_category:
            yield tup

    @property
    def form_val_upname(self):
        """list of tuples (form, value, name.upper()) from the database"""
        if self._form_val_upname is None:
            self._form_val_upname = [(form, val, name.upper())
                                     for (form, val, name) in self]
        return self._form_val_upname

    @property
    def form_upnames_vals(self):
        """list of tuples (form, upnames_vals) from the database
        where upnames_vals is a dictionary
            {name.upper(): all values for this (surface, name)}.

        """
        if self._form_upnames_vals is None:
            # Construct the mapping surface -> category -> [values],
            # capturing homonyms within their category.
            upnames_vals4form = defaultdict(lambda: defaultdict(list))
            for form, val, upname in self.form_val_upname:
                upnames_vals4form[form][upname].append(val)
            self._form_upnames_vals = \
                [(form, dict(upnames_vals))
                 for (form, upnames_vals) in
                 sorted(upnames_vals4form.viewitems(),
                        key=lambda item: -len(item[0]))]
        return self._form_upnames_vals

    def load(self, file_name):
        db_mod = load_as_module(file_name, force=True)
        if not hasattr(db_mod, 'database'):
            raise SLUException("The category label database does not define "
                               "the `database' object!")
        self.database = db_mod.database

        self.normalise_database()
        # Update derived data structures.
        self.gen_synonym_value_category()
        self._form_val_upname = None
        self._form_upnames_vals = None

    def normalise_database(self):
        """Normalise database. E.g., split utterances into sequences of words.
        """
        for name in self.database:
            for value in self.database[name]:
                self.database[name][value] = map(
                    lambda phrase: tuple(phrase.split()),
                    self.database[name][value])

    def gen_synonym_value_category(self):
        for name in self.database:
            for value in self.database[name]:
                for form in self.database[name][value]:
                    self.synonym_value_category.append((form, value, name))
        # Sort the triples from those with most words to those with fewer
        # words.
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
        """Normalises the input utterances (the output of an ASR engine).

        E.g., it removes filler words such as UHM, UM, etc., converts "I'm"
        into "I am", etc.

        """

        utterance.lower()

        for mapping in self.text_normalization_mapping:
            utterance.replace(mapping[0], mapping[1])

        return utterance

    # TODO Update the docstring for the `all_options' argument.
    def values2category_labels_in_utterance(self, utterance, all_options=False):
        """Replaces strings matching surface forms in the label database with
        their slot names plus index.

        NOT IMPLEMENTED YET:
        Since multiple slots can have the same surface form, the return value,
        in general, may comprise of multiple alternatives.

        Arguments:
            utterance -- an instance of the Utterance class where the
                         substitutions should be done

        Returns a tuple of:
            [0] an utterance with replaced database values, and
            [1] a dictionary mapping from category labels to the tuple (slot
                value, surface form).

        """
        utterance_cp = copy.deepcopy(utterance)

        category_label_counter = defaultdict(int)
        valform_for_cl = {}
        if all_options:
            matched_phrases = {}
            match_options = {}

        # FIXME This iterative matching will get slow with larger surface ->
        # slot_value mappings.
        utt_len = len(utterance)  # number of words in the utterance
        substituted_len = 0       # number of words substituted
        # for surface, value, slot_upper in self.cldb.form_val_upname:
        for surface, upnames_vals in self.cldb.form_upnames_vals:
            # In case there is another value for a surface already matched,
            # if all_options:
            #     if surface in matched_phrases:
            #         slots_upper, catlabs_upper = matched_phrases[surface]
            #         # Check whether the slot matched now has already been matched
            #         # before, or if this is a new one.
            #         if slot_upper in slots_upper:
            #             catlab = catlabs_upper[slots_upper.index(slot_upper)]
            #         else:
            #             catlab = '{cat}-{idx}'.format(
            #                 cat=slot_upper,
            #                 idx=category_label_counter[slot_upper])
            #             matched_phrases[surface].append((slot_upper, catlab))
            #         continue
            # NOTE it is ensured the longest matches will always be used in
            # preference to shorter matches, due to the iterated values being
            # sorted by `surface' length from the longest to the shortest.
            if surface in utterance_cp:
                substituted_len += len(surface)
                if all_options:
                    match_idx = len(matched_phrases)
                    matched_phrases.append(surface)
                    match_options.append(upnames_vals.viewitems())
                    utterance_cp.replace(surface,
                                         ['__MATCH-{i}__'.format(i=match_idx)])
                else:
                    # Choose a random category from the known ones.
                    slot_upper, vals = upnames_vals.iteritems().next()
                    # Choose a random value from the known ones.
                    value = vals[0]
                    # Generate the category label.
                    category_label = '{cat}-{idx}'.format(
                        cat=slot_upper,
                        idx=category_label_counter[slot_upper])
                    category_label_counter[slot_upper] += 1
                    # Do the substitution.
                    valform_for_cl[category_label] = (value, surface)
                    # Assumes the surface strings don't overlap.
                    # FIXME: Perhaps replace all instead of just the first one.
                    utterance_cp.replace(surface, [category_label])

                # If nothing is left to replace, stop iterating the database.
                if substituted_len >= utt_len:
                    assert substituted_len == utt_len
                    break

        if all_options:
            # TODO Construct all the possible resulting utterances.
            utterances = list()
            catlab_sub_idxs = defaultdict(lambda: [-1] * len(match_options))
            for subs in product(*match_options):
                utterance_cpcp = copy.deepcopy(utterance_cp)
                for sub_idx, upname_vals in enumerate(subs):
                    upname, vals = upname_vals
                    # Find the correct index for this catlab.
                    cl_idxs = catlab_sub_idxs[upname]
                    cl_idx = cl_idxs[sub_idx]
                    if cl_idx == -1:
                        last_cl_idx = max(cl_idxs)
                        cl_idx = cl_idxs[sub_idx] = last_cl_idx + 1
                    catlab = '{cat}-{idx}'.format(cat=upname, idx=cl_idx)
                    # Replace this match.
                    utterance_cpcp.replace(['__MATCH-{i}__'.format(i=sub_idx)],
                                           [catlab])
                    # TODO Remember the mapping from the catlab.
                utterances.append(utterance_cpcp)
            raise NotImplementedError()

        return utterance_cp, valform_for_cl

    def values2category_labels_in_da(self, utterance, da):
        """Replaces strings matching surface forms in the label database with
        their slot names plus index both in `utterance' and `da' in
        a consistent fashion.

        NOT IMPLEMENTED YET:
        Since multiple slots can have the same surface form, the return value,
        in general, may comprise of multiple alternatives.

        Arguments:
            utterance -- an instance of Utterance where the substitutions
                         should be done
            da -- an instance of DialogueAct where the substitutions should be
                  done

        Returns a tuple of:
            [0] an utterance with replaced database values,
            [1] the DA with replaced database values, and
            [2] a dictionary mapping from category labels to the tuple (slot
                value, surface form).

        """
        # Do the substitution in the utterance, and obtain the resulting
        # mapping.
        utterance, valform_for_cl = self.values2category_labels_in_utterance(
            utterance)
        cl_for_value = {item[1][0]: item[0]
                        for item in valform_for_cl.iteritems()}

        # Using the mapping, perform the same substitution also in all the
        # DAIs.
        da = copy.deepcopy(da)
        for dai in da:
            if dai.value in cl_for_value:
                dai.value2category_label(cl_for_value[dai.value])

        return utterance, da, valform_for_cl

    def category_labels2values_in_utterance(self, utterance, category_labels):
        """Reverts the effect of the values2category_labels_in_utterance(...)
        function.

        Returns the original utterance.
        """
        utterance = copy.deepcopy(utterance)

        for cl in category_labels:
            utterance.replace([cl, ], category_labels[cl][1])

        return utterance

    def category_labels2values_in_da(self, da, category_labels=None):
        """Reverts the effect of the values2category_labels_in_da(...)
        function.

        Returns the original dialogue act.
        """
        da = copy.deepcopy(da)
        for dai in da.dais:
            dai.category_label2value(category_labels)
        return da

    def category_labels2values_in_nblist(self, nblist, category_labels=None):
        """Reverts the effect of the values2category_labels_in_da(...)
        function.

        Returns the converted N-best list.
        """
        nblist = copy.deepcopy(nblist)
        for _, da in nblist.n_best:
            for dai in da:
                dai.category_label2value(category_labels)
        return nblist

    def category_labels2values_in_confnet(self, confnet, category_labels=None):
        """Reverts the effect of the values2category_labels_in_da(...)
        function.

        Returns the converted confusion network.
        """
        confnet = copy.deepcopy(confnet)
        for _, dai in confnet.cn:
            dai.category_label2value(category_labels)
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
