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
from alex.components.slu.da import DialogueActItem, DialogueActFeatures, \
    DialogueActNBListFeatures, DialogueActConfusionNetwork, merge_slu_confnets
from alex.components.slu.exceptions import SLUException
from alex.utils.config import load_as_module
from alex.utils.various import nesteddict


FeatureProps = namedtuple('FeatureProps',
                          ['obs_type', 'feat_class', 'is_abstracted'])
"""properties of types of features this classifier can use

obs_type: name of the observation type from which this type of features
            is extracted (a string)
feat_class: the class for this type of features
is_abstracted: whether this type of observation inherits from Abstracted

Note that names of abstracted observation types have to follow the format
'ab{concrete}' where {concrete} is the name of the non-abstracted type.

"""
# ft_props :: feature type -> feature type properties
ft_props = {
    'ngram': FeatureProps('utt', UtteranceFeatures, False),
    'nbl_ngram': FeatureProps('utt_nbl', UtteranceNBListFeatures, False),
    'cn_ngram': FeatureProps('utt_cn', UtteranceConfusionNetworkFeatures,
                             False),
    'ab_ngram': FeatureProps('abutt', UtteranceFeatures, True),
    'ab_nbl_ngram': FeatureProps('abutt_nbl', UtteranceNBListFeatures,
                                 True),
    'ab_cn_ngram': FeatureProps('abutt_cn',
                                UtteranceConfusionNetworkFeatures, True),
    'prev_da': FeatureProps('prev_da', DialogueActFeatures, False),
    # Following gets used when doing reranking.
    'da_nbl': FeatureProps('da_nbl', DialogueActNBListFeatures, False), }
ft_default_args = {
    'ngram': ('ngram', 4,),
    'nbl_ngram': ('ngram',),
    'cn_ngram': ('ngram', 4,),
    'ab_ngram': ('ngram', 4,),
    'ab_nbl_ngram': ('ngram',),
    'ab_cn_ngram': ('ngram', 4,),
    'prev_da': tuple(),
    'da_nbl': tuple(),
}
ft_default_kwargs = {
    'ngram': {},
    'nbl_ngram': {'size': 4},
    'cn_ngram': {},
    'ab_ngram': {},
    'ab_nbl_ngram': {'size': 4},
    'ab_cn_ngram': {},
    'prev_da': {},
    'da_nbl': {},
}
ft_order = ('ab_ngram', 'ngram',
            'ab_nbl_ngram', 'nbl_ngram',
            'ab_cn_ngram', 'cn_ngram',
            'prev_da', 'da_nbl')


def sort_fts(fts):
    return tuple(sorted(fts, key=ft_order.index))


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
    def __init__(self, file_name):
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

    def load(self, file_name):
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

    # TODO Update the docstring for the `all_options' argument.
    def values2category_labels_in_utterance(self, utterance, all_options=False):
        """Replaces strings matching surface forms in the label database with
        their slot names plus index.

        NOT IMPLEMENTED YET:
        Since multiple slots can have the same surface form, the return value,
        in general, may comprise of multiple alternatives.
        ...To be implemented using Lattice (define in ml.hypothesis, as
        a superclass of Confnet).

        Arguments:
            utterance -- an instance of the Utterance class where the
                         substitutions should be done

        Returns a tuple of:
            [0] an utterance with replaced database values, and
            XXX To be removed.
            [1] a dictionary mapping from category labels to the tuple (slot
                value, surface form).

        """
        # utterance_cp = copy.deepcopy(utterance)
        utterance_cp = AbstractedUtterance.from_utterance(utterance)

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
            #         # Check whether the slot matched now has already been
            #         # matched before, or if this is a new one.
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
                    # FIXME Rework the `all_options' behaviour in general.
                    utterance_cp = utterance_cp.phrase2category_label(
                        surface, ['__MATCH-{i}__'.format(i=match_idx)])
                else:
                    # Choose a random category from the known ones.
                    slot_upper, vals = upnames_vals.iteritems().next()
                    # Choose a random value from the known ones.
                    value = vals[0]
                    # Generate the category label.
                    # category_label = '{cat}-{idx}'.format(
                    # TODO Clean.
                    category_label = '{cat}'.format(
                        cat=slot_upper,
                        idx=category_label_counter[slot_upper])
                    category_label_counter[slot_upper] += 1
                    # Do the substitution.
                    valform_for_cl[category_label] = (value, surface)
                    # Assumes the surface strings don't overlap.
                    # FIXME: Perhaps replace all instead of just the first one.
                    # XXX Temporary solution: we want the new utterance to
                    # contain the <category>=<value> token instead of the
                    # original <surface> sequence of tokens.  This is done
                    # crudely using two subsequent substitutions, so the
                    # original <surface> gets forgotten.
                    utterance_cp = utterance_cp.replace(surface, (value,))
                    utterance_cp = utterance_cp.phrase2category_label(
                        (value,), (category_label,))

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
                    # FIXME Rework the `all_options' behaviour in general.
                    utterance_cpcp = utterance_cpcp.phrase2category_label(
                        ['__MATCH-{i}__'.format(i=sub_idx)], [catlab])
                    # TODO Remember the mapping from the catlab.
                utterances.append(utterance_cpcp)
            raise NotImplementedError()

        return utterance_cp, valform_for_cl

    def values2category_labels_in_uttnblist(self, utt_nblist):
        """
        Replaces strings matching surface forms in the label database with
        their slot names plus index.

        Arguments:
            utt_nblist -- an instance of the UtteranceNBList class where the
                          substitutions should be done

        Returns a tuple of:
            [0] an utterance n-best list with replaced database values, and
            [1] a dictionary mapping from category labels to the tuple (slot
                value, surface form).

        """
        nblist_cp = copy.deepcopy(utt_nblist)

        category_label_counter = defaultdict(int)
        valform_for_cl = {}

        # FIXME This iterative matching will get slow with larger surface ->
        # slot_value mappings.
        tot_len = sum(len(hyp[1]) for hyp in nblist_cp)  # total number of
                                       # words in utterances on the n-best list
        substituted_len = 0       # number of words substituted
        for surface, upnames_vals in self.cldb.form_upnames_vals:
            # NOTE it is ensured the longest matches will always be used in
            # preference to shorter matches, due to the iterated values being
            # sorted by `surface' length from the longest to the shortest.
            hyps_with_surface = [hyp_idx for (hyp_idx, hyp) in
                                 enumerate(nblist_cp) if surface in hyp[1]]
            if hyps_with_surface:
                substituted_len += len(surface) * len(hyps_with_surface)
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
                for hyp_idx in hyps_with_surface:
                    # XXX Temporary solution.  See above for comments on the
                    # use of replace and phrase2category_label.
                    new_utt = nblist_cp[hyp_idx][1].replace(surface, (value,))
                    nblist_cp[hyp_idx][1] = (new_utt.phrase2category_label(
                        (value,), (category_label,)))

                # If nothing is left to replace, stop iterating the database.
                if substituted_len >= tot_len:
                    assert substituted_len == tot_len
                    break

        return nblist_cp, valform_for_cl

    # TODO Test.
    def values2category_labels_in_confnet(self, confnet):
        """
        Replaces strings matching surface forms in the label database with
        their slot names plus index.

        Arguments:
            confnet -- an instance of the UtteranceConfusionNetwork class where
                       the substitutions should be done

        Returns a tuple of:
            [0] a confnet with replaced database values, and
            [1] a dictionary mapping from category labels to the tuple (slot
                value, surface form).

        """
        confnet_cp = copy.deepcopy(confnet)
        valform_for_cl = {}

        # FIXME This iterative matching will get slow with larger surface ->
        # slot_value mappings.
        for surface, upnames_vals in self.cldb.form_upnames_vals:
            # NOTE it is ensured the longest matches will always be used in
            # preference to shorter matches, due to the iterated values being
            # sorted by `surface' length from the longest to the shortest.
            if surface in confnet_cp:
                # Choose a random category from the known ones.
                slot_upper, vals = next(upnames_vals.iteritems())
                # Choose a random value from the known ones.
                value = vals[0]
                # Do the substitution.
                valform_for_cl[slot_upper] = (value, surface)
                # Assumes the surface strings don't overlap.
                # FIXME: Perhaps replace all instead of just the first one.
                # XXX Temporary solution: we want the new confnet to
                # contain the <category>=<value> token instead of the
                # original <surface> sequence of tokens.  This is done
                # crudely using two subsequent substitutions, so the
                # original <surface> gets forgotten.
                confnet_cp = confnet_cp.replace((value,), ('__HIDDEN__',))
                confnet_cp = confnet_cp.replace(surface, (value,))
                confnet_cp = confnet_cp.phrase2category_label(
                    (value,), (slot_upper,))
                confnet_cp = confnet_cp.replace(('__HIDDEN__',), (value,))

        return confnet_cp, valform_for_cl

    def values2catlabs(self, utt_hyp):
        """TODO Document."""
        # Do the substitution in the utterance hypothesis, and obtain the
        # resulting mapping.
        if isinstance(utt_hyp, Utterance):
            return self.values2category_labels_in_utterance(utt_hyp)
        # TODO isinstance(utt_hyp, AbstractedUtterance)
        elif isinstance(utt_hyp, UtteranceNBList):
            # XXX This might not work now.
            return self.values2category_labels_in_uttnblist(utt_hyp)
        else:
            assert isinstance(utt_hyp, UtteranceConfusionNetwork)
            return self.values2category_labels_in_confnet(utt_hyp)

    def values2category_labels_in_da(self, utt_hyp, da):
        """
        Replaces strings matching surface forms in the label database with
        their slot names plus index both in `utt_hyp' and `da' in a consistent
        fashion.

        NOT IMPLEMENTED YET:
        Since multiple slots can have the same surface form, the return value,
        in general, may comprise of multiple alternatives.

        Arguments:
            utt_hyp -- an instance of Utterance or UtteranceNBList where the
                  substitutions should be done
            da -- an instance of DialogueAct where the substitutions should be
                  done

        Returns a tuple of:
            [0] an utterance or utterance n-best list with replaced database
                values,
            [1] the DA with replaced database values, and
            [2] a dictionary mapping from category labels to the tuple (slot
                value, surface form).

        """
        utt_hyp, valform_for_cl = self.values2catlabs(utt_hyp)
        cl_for_value = {item[1][0]: item[0]
                        for item in valform_for_cl.iteritems()}

        # Using the mapping, perform the same substitution also in all the
        # DAIs.
        # TODO Use utt_hyp.iter_instantiations() instead of valform_for_cl.
        da = copy.deepcopy(da)
        for dai in da:
            if dai.value in cl_for_value:
                # combined = '='.join((cl_for_value[dai.value], dai.value))
                # da[idx] = DialogueActItem(dai.dat, dai.name, combined)
                dai.value2category_label(cl_for_value[dai.value])
            # Insist on substituting values with their types, even if not
            # justified by the utterance.
            else:
                matching_triples = [tup for tup in self.cldb.form_val_upname
                                    if tup[1] == dai.value and
                                       tup[2] == dai.name.upper()]
                # Restrict the choice only to the same category.
                if matching_triples:
                    dai.value2category_label(matching_triples[0][2])

        return utt_hyp, da, valform_for_cl

    def category_labels2values_in_utterance(self, utterance, category_labels):
        """Reverts the effect of the values2category_labels_in_utterance()
        function.

        Returns the original utterance.
        """
        # FIXME This causes an error in the copy library. Try running
        # test/test_category_labels_substitution.py
        utterance = copy.deepcopy(utterance)
        for cl in category_labels:
            # FIXME: Use a new method, category_label2phrase, which will know
            # that the new value is not an abstraction for the original one.
            utterance = utterance.phrase2category_label(
                [cl, ], category_labels[cl][1])
        return utterance

    def category_labels2values_in_uttnblist(self, utt_nblist, category_labels):
        """Reverts the effect of the values2category_labels_in_utterance()
        function.

        Returns the original utterance n-best list.
        """
        nblist_cp = copy.deepcopy(utt_nblist)
        for utterance in nblist_cp:
            for cl in category_labels:
                # FIXME: Use a new method, category_label2phrase, which will
                # know that the new value is not an abstraction for the
                # original one.
                utterance = utterance.phrase2category_label(
                    [cl, ], category_labels[cl][1])
        return nblist_cp

    def category_labels2values_in_da(self, da, category_labels=None):
        """Reverts the effect of the values2category_labels_in_da()
        function.

        Returns the original dialogue act.
        """
        da = copy.deepcopy(da)
        for dai in da.dais:
            dai.category_label2value(category_labels)
        return da

    def category_labels2values_in_nblist(self, nblist, category_labels=None):
        """Reverts the effect of the values2category_labels_in_da()
        function.

        Returns the converted N-best list.
        """
        nblist = copy.deepcopy(nblist)
        for _, da in nblist.n_best:
            for dai in da:
                dai.category_label2value(category_labels)
        return nblist

    # Originally called category_labels2values_in_confnet, which caused
    # confusion (since here we deal with DA confnets, as opposed to utterance
    # confnets in other method).
    def category_labels2values_in_dacn(self, confnet, category_labels=None):
        """
        Reverts the effect of the values2category_labels_in_da() method.

        Returns the converted DA confusion network.
        """
        confnet = copy.deepcopy(confnet)
        for _, dai in confnet.cn:
            dai.category_label2value(category_labels)
        return confnet


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

    def __init__(self, preprocessing, cfg=None, *args, **kwargs):
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
