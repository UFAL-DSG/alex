#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is almost PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

import copy

from collections import defaultdict, namedtuple
from itertools import product

from alex.components.asr.utterance import AbstractedUtterance, Utterance, \
    UtteranceConfusionNetwork, UtteranceHyp, UtteranceNBList, \
    UtteranceFeatures, UtteranceNBListFeatures, \
    UtteranceConfusionNetworkFeatures
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork, merge_slu_confnets
from alex.components.slu.exceptions import SLUException
from alex.utils.config import load_as_module
from alex.utils.various import nesteddict

class CategoryLabelDatabase(object):
    """Provides a convenient interface to a database of slot value pairs aka
    category labels.

    Attributes:
        synonym_value_category: a list of (form, value, category label) tuples

    Mapping surface forms to category labels
    ----------------------------------------

    In an utterance:

    - there can be multiple surface forms in an utterance
    - surface forms can overlap
    - a surface form can map to multiple category labels

    Then when detecting surface forms / category labels in an utterance:

    #. find all existing surface forms / category labels and generate a new utterance with for every found surface form and
       category label (called abstracted), where the original surface form is replaced by its category label

       - instead of testing all surface forms from the CLDB from the longest to the shortest in the utterance, we test
         all the substrings in the utterance from the longest to the shortest


    """
    def __init__(self, file_name=None):
        self.database = {}
        self.synonym_value_category = []
        self.forms = []
        self.form_value_cl = []
        self.form2value2cl = nesteddict()

        if file_name:
            self.load(file_name)

        # Bookkeeping.
        self._form_val_upname = None
        self._form_upnames_vals = None

    def __iter__(self):
        """Yields tuples (form, value, category) from the database."""
        for tup in self.synonym_value_category:
            yield tup

    @property
    def form_val_upname(self):
        """list of tuples (form, value, name.upper()) from the database"""
        if self._form_val_upname is None:
            self._form_val_upname = [(form, val, name.upper()) for (form, val, name) in self]
        return self._form_val_upname

    @property
    def form_upnames_vals(self):
        """list of tuples (form, upnames_vals) from the database
        where upnames_vals is a dictionary
            {name.upper(): all values for this (form, name)}.

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
                 sorted(upnames_vals4form.viewitems(), key=lambda item:-len(item[0]))]
        return self._form_upnames_vals

    def load(self, file_name=None, db_mod=None):
        if not db_mod:
            db_mod = load_as_module(file_name, force=True)
            if not hasattr(db_mod, 'database'):
                raise SLUException("The category label database does not define the `database' object!")
        self.database = db_mod.database

        self.normalise_database()
        # Update derived data structures.
        self.gen_synonym_value_category()
        self.gen_form_value_cl_list()
        self.gen_mapping_form2value2cl()

        self._form_val_upname = None
        self._form_upnames_vals = None

    def normalise_database(self):
        """Normalise database. E.g., split utterances into sequences of words.
        """
        new_db = dict()
        for name in self.database:
            new_db[name] = dict()
            for value in self.database[name]:
                new_db[name][value] = [tuple(form.split()) for form in self.database[name][value]]
        self.database = new_db

    def gen_synonym_value_category(self):
        for name in self.database:
            for value in self.database[name]:
                for form in self.database[name][value]:
                    self.synonym_value_category.append((form, value, name))
        # Sort the triples from those with most words to those with fewer
        # words.
        self.synonym_value_category.sort(
            key=lambda svc: len(svc[0]), reverse=True)

    def gen_form_value_cl_list(self):
        """
        Generates an list of form, value, category label tuples from the database. This list is ordered where the tuples
        with the longest surface forms are at the beginning of the list.

        :return: none
        """
        for cl in self.database:
            for value in self.database[cl]:
                for form in self.database[cl][value]:
                    self.form_value_cl.append((form, value, cl))

        self.form_value_cl.sort(key=lambda fvc: len(fvc[0]), reverse=True)

    def gen_mapping_form2value2cl(self):
        """
        Generates an list of form, value, category label tuples from the database . This list is ordered where the tuples
        with the longest surface forms are at the beginning of the list.

        :return: none
        """

        for cl in self.database:
            for value in self.database[cl]:
                for form in self.database[cl][value]:
                    self.form2value2cl[form][value][cl] = 1
                    self.forms.append(form)

        self.forms.sort(key=lambda f: len(f), reverse=True)


class SLUPreprocessing(object):
    """Implements preprocessing of utterances or utterances and dialogue acts.
    The main purpose is to replace all values in the database by their category
    labels (slot names) to reduce the complexity of the input utterances.

    In addition, it implements text normalisation for SLU input, e.g. removing
    filler words such as UHM, UM etc., converting "I'm" into "I am" etc.  Some
    normalisation is hard-coded. However, it can be updated by providing
    normalisation patterns.

    """
    text_normalization_mapping = [(['erm', ], []),
                                  (['uhm', ], []),
                                  (['um', ], []),
                                  (["i'm", ], ['i', 'am']),
                                  (['(sil)', ], []),
                                  (['(%hesitation)', ], []),
                                  (['(hesitation)', ], []),
                                  ]

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

    def normalise_utterance(self, utterance):
        """
        Normalises the utterance (the output of an ASR).

        E.g., it removes filler words such as UHM, UM, etc., converts "I'm"
        into "I am", etc.

        """
        utterance.lower()

        for mapping in self.text_normalization_mapping:
            utterance = utterance.replace_all(mapping[0], mapping[1])
        return utterance

    def normalise_nblist(self, nblist):
        """
        Normalises the N-best list (the output of an ASR).

        :param nblist:
        :return:
        """

        unb = copy.deepcopy(nblist)
        for utt_idx, hyp in enumerate(unb):
            unb[utt_idx][1] = self.normalise_utterance(hyp[1])
        return unb

    def normalise_confnet(self, confnet):
        """
        Normalises the confnet (the output of an ASR).

        E.g., it removes filler words such as UHM, UM, etc., converts "I'm"
        into "I am", etc.

        """
        confnet.lower()
        for mapping in self.text_normalization_mapping:
            confnet = confnet.replace(mapping[0], mapping[1])
        return confnet

    def normalise(self, utt_hyp):
        if isinstance(utt_hyp, Utterance):
            return self.normalise_utterance(utt_hyp)
        elif isinstance(utt_hyp, UtteranceNBList):
            return self.normalise_nblist(utt_hyp)
        elif isinstance(utt_hyp, UtteranceConfusionNetwork):
            return self.normalise_confnet(utt_hyp)
        else:
            raise SLUException("Unsupported observations.")


# XXX This in fact is not an interface anymore (for it has a constructor).  It
# had better be called AbstractSLU.
class SLUInterface(object):
    """
    Defines a prototypical interface each SLU parser should provide.

    It should be able to parse:
      1) an utterance hypothesis (an instance of UtteranceHyp)
          - output: an instance of SLUHypothesis

      2) an n-best list of utterances (an instance of UtteranceNBList)
          - output: an instance of SLUHypothesis

      3) a confusion network (an instance of UtteranceConfusionNetwork)
          - output: an instance of SLUHypothesis

    """

    def __init__(self, preprocessing, cfg, *args, **kwargs):
        self.preprocessing = preprocessing
        self.cfg = cfg

    # TODO Document the methods.
    def extract_features(self, *args, **kwargs):
        pass

    def prune_features(self, *args, **kwargs):
        pass

    def prune_classifiers(self, *args, **kwargs):
        pass

    def print_classifiers(self, *args, **kwargs):
        pass

    def train(self, *args, **kwargs):
        pass

    def save_model(self, *args, **kwargs):
        pass

    def parse_1_best(self, obs, *args, **kwargs):
        # TODO Document.
        raise SLUException("Not implemented")

    def parse_nblist(self, obs, *args, **kwargs):
        """
        Parses an observation featuring an utterance n-best list using the
        parse_1_best method.

        Arguments:
            obs -- a dictionary of observations
                :: observation type -> observed value
                where observation type is one of values for `obs_type' used in
                `ft_props', and observed value is the corresponding observed
                value for the input
            args -- further positional arguments that should be passed to the
                `parse_1_best' method call
            kwargs -- further keyword arguments that should be passed to the
                `parse_1_best' method call

        """
        nblist = obs['utt_nbl']
        if len(nblist) == 0:
            return DialogueActConfusionNetwork()

        obs_wo_nblist = copy.deepcopy(obs)
        del obs_wo_nblist['utt_nbl']
        dacn_list = []
        for prob, utt in nblist:
            if "_other_" == utt:
                dacn = DialogueActConfusionNetwork()
                dacn.add(1.0, DialogueActItem("other"))
            elif "_silence_" == utt:
                dacn = DialogueActConfusionNetwork()
                dacn.add(1.0, DialogueActItem("silence"))
            else:
                obs_wo_nblist['utt'] = utt
                dacn = self.parse_1_best(obs_wo_nblist, *args, **kwargs)

            dacn_list.append((prob, dacn))

        dacn = merge_slu_confnets(dacn_list)
        dacn.prune()
        dacn.sort()

        return dacn

    def parse_confnet(self, obs, n=40, *args, **kwargs):
        """
        Parses an observation featuring a word confusion network using the
        parse_nblist method.

        Arguments:
            obs -- a dictionary of observations
                :: observation type -> observed value
                where observation type is one of values for `obs_type' used in
                `ft_props', and observed value is the corresponding observed
                value for the input
            n -- depth of the n-best list generated from the confusion network
            args -- further positional arguments that should be passed to the
                `parse_1_best' method call
            kwargs -- further keyword arguments that should be passed to the
                `parse_1_best' method call

        """

        # Separate the confnet from the observations.
        confnet = obs['utt_cn']
        obs_wo_cn = copy.deepcopy(obs)
        del obs_wo_cn['utt_cn']

        # Generate the n-best list from the confnet.
        obs_wo_cn.setdefault('utt_nbl', confnet.get_utterance_nblist(n=n))
        # Parse the n-best list.
        return self.parse_nblist(obs_wo_cn, *args, **kwargs)

    def parse(self, obs, *args, **kwargs):
        """Check what the input is and parse accordingly."""

        # For backward compatibility, accept `obs' as a single observation
        # type.
        if not isinstance(obs, dict):
            obs = {'asr_hyp': obs}

        # Process the generic ASR hypothesis (of unknown type).
        if 'asr_hyp' in obs:
            asr_hyp = obs['asr_hyp']
            if isinstance(asr_hyp, Utterance):
                obs.setdefault('utt', asr_hyp)
            elif isinstance(asr_hyp, UtteranceHyp):
                obs.setdefault('utt', asr_hyp.utterance)
            elif isinstance(asr_hyp, UtteranceNBList):
                obs.setdefault('utt_nbl', asr_hyp)
            elif isinstance(asr_hyp, UtteranceConfusionNetwork):
                obs.setdefault('utt_cn', asr_hyp)
            del obs['asr_hyp']

        # Decide what method to use based on the most complex input
        # representation.
        # (TODO: Get rid of this scheme of using three different methods.)
        if 'utt_cn' in obs:
            return self.parse_confnet(obs, *args, **kwargs)
        elif 'utt_nbl' in obs:
            return self.parse_nblist(obs, *args, **kwargs)
        else:
            return self.parse_1_best(obs, *args, **kwargs)

        # raise DAILRException("Unsupported input in the SLU component.")
