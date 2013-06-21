#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from collections import defaultdict, namedtuple
import copy
import cPickle as pickle
from itertools import izip, repeat
from math import isnan
import numpy as np
from operator import add, itemgetter
import random
from scipy.sparse import csr_matrix, vstack
import sys

from sklearn import metrics, tree
from sklearn.linear_model import LogisticRegression

# TODO Rewrite using lazy imports.
from alex.components.asr.utterance import UtteranceFeatures, \
    UtteranceNBListFeatures, UtteranceConfusionNetworkFeatures, UtteranceHyp
from alex.components.slu import base
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork, DialogueActFeatures, \
    DialogueActNBListFeatures, merge_slu_confnets
from alex.components.slu.exception import SLUException
from alex.ml.features import Features
from alex.utils.various import crop_to_finite

from exception import DAILRException


def get_features_from_tree(tree):
    """Returns features used in an sklearn decision tree."""
    n_nodes = tree.tree_.node_count
    left = tree.tree_.children_left
    right = tree.tree_.children_right
    feats = tree.tree_.feature
    return [feat for (feat, left, right) in izip(feats, left, right)
            if 0 <= left < n_nodes and 0 <= right < n_nodes]


class DAILogRegClassifier(base.SLUInterface):
    """
    Implements learning of and decoding with dialogue act item classifiers
    based on logistic regression.

    When used for parsing an utterance, each classifier decides whether its
    respective dialogue act item is present.  Then, the output dialogue act is
    constructed by joining all detected dialogue act items.

    Dialogue act is defined as a composition of dialogue act items. E.g.

    confirm(drinks="wine")&inform(name="kings shilling")
        <=> 'does kings serve wine'

    where confirm(drinks="wine") and inform(name="kings shilling") are two
    dialogue act items.


    Attributes:
        category_labels: mapping { utterance ID:
                                    { category label: original string } }
        cls_threshold: threshold for classifying as positive
                       to be DEPRECATED
        cls_thresholds: thresholds for classifying as positive, one for each
                        classifier trained
        clser_type: a string indicating type of the classifier used
                    currently supported choices: 'logistic', 'tree'
        dai_counts: mapping { DAI: number of occurrences in data }
        das: mapping { utterance ID: DA } for DAs corresponding to training
             utterances
        feat_counts: mapping { feature: number of occurrences }
        feature_idxs: mapping { feature: feature index }; feature indices span
                      range(0, number_of_features)
        features_size: size (order) of features, i.e., length of the n-grams
        features_type: type of features (see below for details)
        input_matrix: observation matrix, a numpy array with rows corresponding
                      to utterances and columns corresponding to features
                      This is a read-only attribute.
        output_matrix: mapping { DAI: [ utterance index:
                                        ?DAI present in utterance ] }
                       where the list is a numpy array, and the values are
                       either 0.0 or 1.0
                       This is a read-only attribute.
        preprocessing: an SLUPreprocessing object to be used for preprocessing
                       of utterances and DAs
        trained_classifiers: mapping { DAI: classifier for this DAI }
        utt_ids: IDs of training utterances / utterance hypotheses (n-best
                 lists)
        utterance_features: mapping { utterance ID: utterance features } where
                            the features is an instance of Features
        # utterances: mapping { utterance ID: utterance } for training
        #             utterances

    Type of features:
        By default, 'ngram' is used, meaning n-grams up to order 4 plus all
        skip n-grams of maximally that order are extracted.

        The argument specifying the type of features should be a sequence of
        strings determining what types of features will be in use.  The
        following values are recognised:

            'ngram': n-grams (as described above)
            'nbl_ngram': n-grams on utterance n-best lists
            'cn_ngram': n-grams on utterance confusion networks
            'ab_ngram': n-grams on abstracted utterances (with substitutions)
            'ab_cn_ngram': n-grams on abstracted utterance confusion networks
            'prev_da': features of the DA preceding to the one to be classified
            'da_nbl': features of a DA n-best list (output from SLU,
                      presumably)

    """
    # TODO Document attributes from the original DAILogRegClassifier class
    # (from the load_model method on).
    # TODO Document changes made in slot value abstraction for DSTC.
    # TODO Document intercepts, coefs.

    # TODO Document.
    def __init__(self,
                 preprocessing=None,
                 clser_type='logistic',
                 features_type='ngram',
                 ft_args=dict(),
                 ft_kwargs=dict(),
                 # features_size=4,
                 abstractions=('concrete', 'abstract'),
                 cfg=None):
        """TODO

        Arguments (partial listing):
            abstractions: what abstractions to do with DAs:
                'concrete' ... include concrete DAs
                'partial'  ... include DAs instantiated with do_abstract=False
                'abstract' ... include DAs instantiated with do_abstract=True
                (default: ('concrete', 'partial', 'abstract'))
            cfg: currently ignored (included after it was added to
                SLUInterface constructor)

        """
        # FIXME: maybe the SLU components should use the Config class to
        # initialise themselves.  As a result it would create their category
        # label database and pre-processing classes.
        random.seed()

        # Save the arguments.
        self.preprocessing = preprocessing
        self.clser_type = clser_type
        if clser_type == 'logistic':
            self.intercepts = dict()
            self.coefs = dict()
        self.features_type = features_type
        self.ft_args = copy.deepcopy(base.ft_default_args)
        self.ft_args.update(ft_args)
        self.ft_kwargs = copy.deepcopy(base.ft_default_kwargs)
        self.ft_kwargs.update(ft_kwargs)

        # TODO Deprecate.
        # self.features_size = features_size

        self.abstractions = abstractions

        # Additional bookkeeping.
        # Setting protected fields to None is interpreted as that they have to
        # be computed yet.
        self.cls_threshold = 0.5
        self.cls_thresholds = defaultdict(lambda: 0.5)
        # self.abutterances = None
        # self.abutt_nblists = None
        self.n_feat_sets = 0
        self._do_abstract_values = set()
        if 'partial' in abstractions:
            self._do_abstract_values.add(False)
        if 'abstract' in abstractions:
            self._do_abstract_values.add(True)
        self._dai_counts = None
        self._input_matrix = None
        self._output_matrix = None
        self._default_min_feat_count = 1
        self._default_min_conc_feat_count = 1
        self._default_min_correct_dai_count = 1
        self._default_min_incorrect_dai_count = 1

    # XXX A hack.  To do this in a principled fashion, we would need to name
    # different kinds of features in use in some class field.
    def _get_conc_feats_idxs(self):
        cur_idx = 0
        conc_idxs = list()
        # Mimick the process of extracting features, note down indices of
        # features that are concrete.
        if 'ngram' in self.features_type:
            for do_abstract in self._do_abstract_values:
                cur_idx += 1
            if 'concrete' in self.abstractions:
                conc_idxs.append(cur_idx)
                cur_idx += 1
        # That's it for now.  Currently, we don't consider any other features
        # concrete.
        return conc_idxs

    def _extract_feats_from_one(self, obss, inst=None, utt_id=None):
        """
        Extracts features for a single input, characterised by potentially many
        types of observations (the utterance, the previous dialogue act etc.).

        Arguments:
            obss -- a mapping {<observation type>: <observation>}. For
                a listing of recognised observation types, consult
                DAILogRegClassifier.obs_props.
            inst -- either a single instantiation as a tuple (type, value),
                'all', or None.  In the first case, the observations that can
                be instantiated are instantiated for type=value.  In the second
                case, features are extracted from all possible instantiations
                of the observations.  In the last case, only the concrete
                observations are used to extract features.
            utt_id -- If specified, each `obss[ft]', `ft' being various feature
                types, is expected to be a dictionary mapping utterance IDs to
                their respective observation.  ID of the utterance for which
                features should be extracted is then given in this argument.

        """
        # fs = self.features_size
        ft_props = base.ft_props

        # # Determine the actual class of `utterance'.
        # utt_features_cls = UtteranceFeatures
        # if utt_hyp is not None:
            # if isinstance(utt_hyp, Utterance):
                # utt_features_cls = UtteranceFeatures
            # else:
                # assert isinstance(utt_hyp, UtteranceConfusionNetwork)
                # utt_features_cls = UtteranceConfusionNetworkFeatures
        # # Determine the actual class of `abutt_hyp'.
        # abutt_features_cls = UtteranceFeatures
        # if abutt_hyp is not None:
            # if isinstance(abutt_hyp, Utterance):
                # abutt_features_cls = UtteranceFeatures
            # else:
                # assert isinstance(abutt_hyp, UtteranceConfusionNetwork)
                # abutt_features_cls = UtteranceConfusionNetworkFeatures

        # Collect all types of features.
        feat_sets = list()

        for ft in self.features_type:
            this_ft_props = ft_props[ft]
            obs_type = this_ft_props.obs_type
            if utt_id is None:
                obs = obss.get(obs_type, None)
            else:
                obs = obss.get(obs_type, dict()).get(utt_id, None)
            # Handle the case of a missing observation.
            if obs is None:
                if this_ft_props.is_abstracted:
                    for abstraction_type in self.abstractions:
                        feat_sets.append(Features())
                else:
                    feat_sets.append(Features())
            # If the observation is in place,
            else:
                feat_class = this_ft_props.feat_class
                this_ft_args = self.ft_args[ft]
                this_ft_kwargs = self.ft_kwargs[ft]
                if this_ft_props.is_abstracted:
                    if inst == 'all':
                        for do_abstract in self._do_abstract_values:
                            feat_list = list()
                            for instion in obs.all_instantiations:
                                new_feats = feat_class(*this_ft_args,
                                                       **this_ft_kwargs)
                                new_feats.parse(instion)
                                feat_list.append(new_feats)
                            feats = Features.join(feat_list, distinguish=False)
                            # Features values can hereby get quite high, but
                            # that's alright, as there will also be
                            # correspondingly many training examples generated
                            # from this observation.
                            feat_sets.append(feats)
                    elif inst is None:
                        for do_abstract in self._do_abstract_values:
                            feat_sets.append(Features())
                    else:
                        # `inst' is an instantiation: (type_, value)
                        for do_abstract in self._do_abstract_values:
                            obs_inst = obs.instantiate(
                                inst[0], inst[1], do_abstract=do_abstract)
                            new_feats = feat_class(*this_ft_args,
                                                   **this_ft_kwargs)
                            new_feats.parse(obs_inst)
                            feat_sets.append(new_feats)

                    if 'concrete' in self.abstractions:
                        new_feats = feat_class(*this_ft_args,
                                               **this_ft_kwargs)
                        new_feats.parse(obs)
                        feat_sets.append(new_feats)
                else:  # if this type of features does not allow abstraction,
                    new_feats = feat_class(*this_ft_args, **this_ft_kwargs)
                    new_feats.parse(obs)
                    feat_sets.append(new_feats)
        # # TODO!! Generalise (compress the code).
        # if 'ngram' in self.features_type:
        #     if inst == 'all':
        #         for do_abstract in self._do_abstract_values:
        #             feats = Features.join(
        #                 (abutt_features_cls('ngram', fs, inst)
        #                  for inst in
        #                  abutt_hyp.all_instantiations(do_abstract)),
        #                 distinguish=False)
        #             # Features values can hereby get quite high, but that's
        #             # alright, as there will also be correspondingly many
        #             # training examples generated from this utt_hyp.
        #             feat_sets.append(feats)
        #         if 'concrete' in self.abstractions:
        #             feat_sets.append(utt_features_cls('ngram', fs, utt_hyp))
        #     elif inst is None:
        #         for do_abstract in self._do_abstract_values:
        #             feat_sets.append(Features())
        #         feat_sets.append(utt_features_cls('ngram', fs, utt_hyp))
        #     else:
        #         # `inst' is an instantiation: (type_, value)
        #         for do_abstract in self._do_abstract_values:
        #             utt_inst = abutt_hyp.instantiate(
        #                 inst[0], inst[1], do_abstract=do_abstract)
        #             feat_sets.append(abutt_features_cls('ngram', fs,
        #             utt_inst))
        #         if 'concrete' in self.abstractions:
        #             feat_sets.append(utt_features_cls('ngram', fs, utt_hyp))
        #
        # if 'prev_da' in self.features_type:
        #     if prev_da is not None:
        #         feat_sets.append(DialogueActFeatures(prev_da))
        #     else:
        #         feat_sets.append(Features())
        # if 'utt_nbl' in self.features_type:
        #     if utt_nblist is not None:
        #         feat_sets.append(
        #             UtteranceNBListFeatures(size=fs,
        #                                     utt_nblist=utt_nblist))
        #     else:
        #         feat_sets.append(Features())
        # if 'da_nbl' in self.features_type:
        #     if da_nblist is not None:
        #         feat_sets.append(
        #             DialogueActNBListFeatures(da_nblist=da_nblist))
        #     else:
        #         feat_sets.append(Features())

        # Based on the number of distinct feature types, either join them
        # or take the single feature type.
        if len(feat_sets) > 1:
            feats = Features.join(feat_sets)
        elif len(feat_sets) == 1:
            feats = feat_sets[0]
        else:
            # XXX This exception can actually be raised even if we know how
            # to handle that type of features ('prev_da') but don't have
            # the argument specifying the necessary input (prev_das).
            raise DAILRException(
                'Cannot handle this type of features: "{ft}".'
                .format(ft=self.features_type))
        return feats

    def _extract_feats_from_many(self, obss, inst=None):
        # self.n_feat_sets = (
        #     ('ngram' in self.features_type) * len(self.abstractions) +
        #     ('utt_nbl' in self.features_type) * len(self.abstractions) +
        #     ('da_nbl' in self.features_type) * bool(da_nblists))
        self.n_feat_sets = sum(
            (ft in obss) *
            (len(self.abstractions) if base.ft_props[ft].is_abstracted else 1)
            for ft in self.features_type)

        return {utt_id: self._extract_feats_from_one(obss, utt_id=utt_id)
                for utt_id in self.utt_ids}

        # # XXX Why the asymmetry with self.utterances (and not utterances
        # # passed in as an argument)?
        # return {utt_id:
        #         self._extract_feats_from_one(
        #             utt_hyp=(self.utterances[utt_id]
        #                      if self.utterances is not None else None),
        #             abutt_hyp=(self.abutterances[utt_id]
        #                        if self.abutterances is not None else None),
        #             prev_da=(prev_das[utt_id]
        #                      if prev_das is not None else None),
        #             utt_nblist=(utt_nblists[utt_id]
        #                         if utt_nblists is not None else None),
        #             abutt_nblist=(abutt_nblists[utt_id]
        #                           if abutt_nblists is not None else None),
        #             da_nblist=(da_nblists[utt_id]
        #                        if da_nblists is not None else None),
        #             inst=inst)
        #         for utt_id in self.utt_ids}

    def extract_features(self, obss, das, verbose=False):
        """
        TODO Update.

        Extracts features from given utterances or system DAs or utterance
        n-best lists or DA n-best lists, making use of their corresponding DAs.
        This is a pre-requisite to pruning features, classifiers, and running
        training with this learner.

        Arguments:
            utterances: mapping { ID: utterance }, the utterance being an
                instance of the Utterance class (default: None)
            das: mapping { ID: DA }, the DA being an instance of the
                DialogueAct class
                NOTE this argument has a default value, yet it is obligatory.
            prev_das: mapping { ID: DA }, the DA, an instance of the
                DialogueAct class, describing the DA immediately preceding to
                the one in question (default: None)
            utt_nblists: mapping { ID: utterance n-best list }, with the
                utterance n-best list reflecting the ASR output (default: None)
            da_nblists: mapping { ID: DA n-best list }, with the DA n-best list
                reflecting an SLU output (default: None)
            verbose: print debugging output?  More output is printed if
                verbose > 1.

        The dictionary arguments are expected to all have the same set of keys.

        """
        # Save the input observations and the outputs.
        self.das = das
        if obss:
            self.obss = obss
            self.utt_ids = reduce(
                set.union,
                (set(typed_obss.viewkeys())
                 for typed_obss in obss.viewvalues()))
        # self.utterances = utterances
        # self.utt_nblists = utt_nblists
        # if utterances:
        #     self.utt_ids = utterances.keys()
        # elif utt_nblists:
        #     self.utt_ids = utt_nblists.keys()
        # elif da_nblists:
        #     self.utt_ids = da_nblists.keys()
        else:
            raise DAILRException(
                # 'Cannot learn a classifier without utterances and without '
                # 'ASR or SLU hypotheses.')
                'Cannot learn a classifier without any observations.')

        # Normalise the text and substitute category labels.
        self.category_labels = dict()
        if self.preprocessing:
            abstractables = [obs_type
                             for obs_type in ('utt', 'utt_nbl', 'utt_cn')
                             if obs_type in obss]
            if not abstractables:
                raise DAILRException(
                    'Cannot do preprocessing without observed utterance '
                    'hypotheses (transcriptions, n-best lists or confusion '
                    'networks.')
            for concrete_ot in abstractables:
                abs_ot = 'ab' + concrete_ot
                self.obss[abs_ot] = dict()
                for utt_id, utt_hyp in self.obss[concrete_ot].iteritems():
                    if utt_hyp is None:
                        # (FIXME) This should rather be discarded right away.
                        continue
                    self.category_labels[utt_id] = dict()
                    # Normalise the text.
                    self.obss[concrete_ot][utt_id] = utt_hyp = (
                        self.preprocessing.normalise(utt_hyp))
                    # Substitute category labes.
                    self.obss[abs_ot][utt_id], self.das[utt_id], catlabs = (
                        self.preprocessing.values2category_labels_in_da(
                            utt_hyp, self.das[utt_id]))
                    # XXX Not sure whether any key in the dictionary can hereby
                    # get rewritten and whether that would be wrong.  Not sure
                    # about rewriting DAs in the above assignment, either.
                    self.category_labels[utt_id].update(catlabs)

        # Generate utterance features.
        self.utterance_features = self._extract_feats_from_many(
            self.obss, inst='all')
        if verbose:
            print >>sys.stderr, "Done extracting features."
        if verbose >= 2:
            print "Random few extracted features:"
            for utt_id in self.utt_ids[:41]:
                print str(self.utterance_features[utt_id])
            print

    def prune_features(self, min_feature_count=None,
                       min_conc_feature_count=None,
                       verbose=False):
        """Prunes features that occur few times.

        Arguments:
            min_feature_count: minimum number of a feature occurring for it not
                to be pruned (default: 5)
            min_conc_feature_count: minimum number of a concrete feature
                occurring for it not to be pruned (default: 4)
            verbose: whether to print diagnostic messages to stdout; when set
                to a larger value (i.e., 2), causes even higher verbosity
                (default: False)

        """
        # Remember the thresholds used, and use it as a default later.
        if min_feature_count is None:
            min_feature_count = 5
        else:
            self._default_min_feat_count = min_feature_count
        if min_conc_feature_count is None:
            min_conc_feature_count = 4
        else:
            self._default_min_conc_feat_count = min_conc_feature_count
        # Count number of occurrences of features.
        self.feat_counts = dict()
        for utt_id in self.utt_ids:
            for feature in self.utterance_features[utt_id]:
                self.feat_counts[feature] = \
                    self.feat_counts.get(feature, 0) + 1

        if verbose:
            print >>sys.stderr, "Done counting features."
        if verbose:
            print "Number of features: ", len(self.feat_counts)

        # Collect those with too few occurrences.
        if self.n_feat_sets == 1:
            _min_count = (min_conc_feature_count if self._get_conc_feats_idxs()
                          else min_feature_count)
            low_count_features = set(filter(
                lambda feature: self.feat_counts[feature] < _min_count,
                self.feat_counts.iterkeys()))
        else:
            conc_idxs = self._get_conc_feats_idxs()
            low_count_features = set(filter(
                lambda feature: self.feat_counts[feature] < (
                    min_conc_feature_count if feature[0] in conc_idxs else
                    min_feature_count),
                self.feat_counts.iterkeys()))

        # Discard self.utterance_features -- we won't need it anymore.
        self.utterance_features = None
        # for utt_id in self.utt_ids:
            # self.utterance_features[utt_id].prune(low_count_features)

        self.feat_counts = {key: count
                            for (key, count) in self.feat_counts.iteritems()
                            if key not in low_count_features}

        # Build the mapping from features to their indices.
        self.feature_idxs = {}
        feat_idx = 0
        for feature in self.feat_counts:
            self.feature_idxs[feature] = feat_idx
            feat_idx += 1

        # Build the inverse mapping.
        i2f = self.idx2feature = [None] * len(self.feature_idxs)
        for feat, idx in self.feature_idxs.iteritems():
            i2f[idx] = feat

        if verbose:
            print >>sys.stderr, "Done pruning features."
        if verbose:
            print "Number of features after pruning: ", len(self.feat_counts)
            if verbose > 1:
                print "The features:"
                print "---features---"
                import pprint
                pprint.pprint([str(feat) for feat in self.feature_idxs])
                print "---features---"

    @property
    def dai_counts(self):
        """a mapping { DAI : number of occurrences in training DAs }"""
        # If `_dai_counts' have not been evaluated yet,
        if self._dai_counts is None:
            # Count occurrences of all DAIs in the DAs bound to this learner.
            _dai_counts = self._dai_counts = dict()
            for utt_id in self.utt_ids:
                for dai in self.das[utt_id].dais:
                    # bound_dai = AbstractedTuple2((
                        # dai.dat,
                        # '{n}={v}'.format(n=dai.name, v=dai.value)
                        # if (dai.name and dai.value) else (dai.name or '')))
                    # gen_dai = bound_dai.get_generic()
                    gen_dai = dai.get_generic()
                    _dai_counts[gen_dai] = _dai_counts.get(gen_dai, 0) + 1
                    if 'concrete' in self.abstractions and dai != gen_dai:
                        _dai_counts[dai] = _dai_counts.get(dai, 0) + 1
        return self._dai_counts

    def print_dais(self):
        """
        Prints what `extract_classifiers(verbose=True)' would output in
        earlier versions.

        """
        for utt_id in self.utt_ids:
            for dai in self.das[utt_id].dais:
                # XXX What again does ('-' not in dai.value) check? Presence of
                # a category label? This seems to be the case yet it is very
                # cryptic.
                if dai.value and '-' not in dai.value:
                    print '#' * 60
                    print self.das[utt_id]
                    print self.obss['utt'][utt_id]
                    print self.category_labels[utt_id]

    def prune_classifiers(self, min_dai_count=5, min_correct_count=None,
                          min_incorrect_count=None, accept_dai=None):
        """
        Prunes classifiers for DAIs that cannot be reliably classified with
        these training data.

        Arguments:
            min_dai_count: minimum number of occurrences of a DAI for it
                to have its own classifier (this affects only non-atomic DAIs
                without abstracted category labels)
            min_correct_count: ditto, but only DAIs labeled correct are counted
            min_incorrect_count: ditto, but only DAIs labeled incorrect are
                counted
            accept_dai: custom fuction that takes a string representation of
                a DAI and returns True if that DAI should have its classifier,
                else False;

                The function gets called with the following tuple
                of arguments: (self, dai), where `self' is this
                DAILogRegClassifier object, and `dai' the DAI in
                question

        """
        # Store arguments for later use.
        if min_correct_count is not None:
            self._default_min_correct_dai_count = min_correct_count
        if min_incorrect_count is not None:
            self._default_min_incorrect_dai_count = min_incorrect_count
        # Define pruning criteria.
        if accept_dai is not None:
            _accept_dai = lambda dai: accept_dai(self, dai)
        else:
            def _accept_dai(dai):
                # Keep all generic classifiers.
                if dai.is_generic:
                    return True
                # Discard a DAI that is reasonably complex and yet has too few
                # occurrences.
                if (dai.name is not None
                        and dai.value is not None
                        # and not dai.has_category_label()
                        and self._dai_counts[dai] < min_dai_count):
                    return False
                # Discard classifiers in the form `inform(name="[OTHER]")'.
                if dai.value == dai.other_val:
                    return False
                # Hack to pass the unit test without training a larger model.
                # if dai.dat == 'reqalts':
                    # return False
                # Discard a DAI in the form '(slotname="dontcare")'.
                # (Was 'dai.name is not None and ...' but sometimes, dai.name
                # was '' when it was expected to actually be None.)
                if dai.name and dai.value == "dontcare":
                    return False
                # Discard a 'null()'. This classifier can be ignored since the
                # null dialogue act is a complement to all other dialogue acts.
                return not dai.is_null()

        # Do the pruning.
        old_dai_counts = self.dai_counts  # NOTE the side effect from the
                                          # getter
        self._dai_counts = {dai: old_dai_counts[dai]
                            for dai in old_dai_counts
                            if _accept_dai(dai)}

    def print_classifiers(self):
        print "Classifiers detected in the training data"
        print "-" * 60
        print "Number of classifiers: ", len(self.dai_counts)
        print "-" * 60

        for dai in sorted(self.dai_counts.iterkeys()):
            print '{dai:>40} = {cnt}'.format(dai=dai,
                                             cnt=self._dai_counts[dai])
        print "-" * 60
        print

    @property
    def output_matrix(self):
        """the output matrix of DAIs for training utterances

        Note that the output matrix has unusual indexing: first associative
        index to columns, then integral index to rows.

        Beware, this getter will fail if `extract_features' was not called
        before.

        """
        if self._output_matrix is None:
            self.gen_output_matrix()
        return self._output_matrix

    def gen_output_matrix(self):
        """Generates the output matrix from training data.

        Beware, this method will fail if `extract_features' was not called
        before.

        """
        das = self.das
        uts = self.utt_ids
        # NOTE that the output matrix has unusual indexing: first associative
        # index to columns, then integral index to rows.
        self._output_matrix = \
            {dai.extension(): np.array([dai in das[utt_id]
                                        for utt_id in uts])
             for dai in self._dai_counts}

    @property
    def input_matrix(self):
        """
        OBSOLETE

        the input matrix of features for training utterances

        Beware, this getter will fail if `extract_features' was not called
        before.

        """
        if self._input_matrix is None:
            self.gen_input_matrix()
        return self._input_matrix

    def gen_input_matrix(self):
        """
        OBSOLETE

        Generates the observation matrix from training data.

        Beware, this method will fail if `extract_features' was not called
        before.

        """
        self._input_matrix = np.zeros((len(self.utt_ids),
                                       len(self.feat_counts)))
        for utt_idx, utt_id in enumerate(self.utt_ids):
            self._input_matrix[utt_idx] = (
                self.utterance_features[utt_id]
                .get_feature_vector(self.feature_idxs))

    @classmethod
    def balance_data(cls, inputs, outputs):
        outputs_idxs = defaultdict(list)
        for output_idx, output in enumerate(outputs):
            outputs_idxs[output].append(output_idx)
        max_count = max(map(len, outputs_idxs.values()))
        new_inputs = list()
        new_outputs = list()
        for output, output_idxs in outputs_idxs.iteritems():
            n_remains = max_count - len(output_idxs)
            new_inputs.extend(inputs[random.choice(output_idxs), :]
                              for _ in xrange(n_remains))
            new_outputs.extend([output] * n_remains)
        # (The following check is to avoid ValueError from numpy.concatenate of
        # an empty list.)
        # If any balancing was done,
        if new_outputs:
            # Return a new, balanced set.
            new_inputs = vstack(new_inputs)
            return (vstack((inputs, new_inputs)),
                    np.concatenate((outputs, new_outputs)))
        else:
            # Return the original inputs and outputs.
            return inputs, outputs

    def train(self, sparsification=1.0, min_feature_count=None,
              min_correct_dai_count=None, min_incorrect_dai_count=None,
              balance=True, calibrate=True, verbose=True):
        if min_feature_count is None:
            min_feature_count = self._default_min_feat_count
        if min_correct_dai_count is None:
            min_correct_dai_count = self._default_min_correct_dai_count
        if min_incorrect_dai_count is None:
            min_incorrect_dai_count = self._default_min_incorrect_dai_count

        # Train classifiers for every DAI less those that have been pruned.
        self.trained_classifiers = {}
        # if calibrate:
            # calib_data = list()
        if verbose:
            coefs_abs_sum = np.zeros(shape=(1, len(self.feature_idxs)))

        for dai in sorted(self._dai_counts):
            # before message
            if verbose:
                print >>sys.stderr, "Training classifier: ", unicode(dai)
                print "Training classifier: ", unicode(dai)
                print >>sys.stderr, "  - extracting features...", unicode(dai)

            # (TODO) We might want to skip this based on whether NaNs were
            # considered in the beginning.  That might be specified in an
            # argument to the initialiser.

            # Instantiate inputs and outputs for the current classifier.
            # TODO Check this does what was intended. Simplify.
            dai_dat = dai.dat
            dai_slot = dai.name
            dai_catlab = dai.value
            dai_catlab_words = (tuple(dai_catlab.split()) if dai_catlab
                                else tuple())
            if dai.is_generic:
                compatible_insts = (lambda utt:
                                    utt.insts_for_type(dai_catlab_words))
            else:
                try:
                    dai_val_proper = next(iter(dai.orig_values))
                except StopIteration:
                    dai_val_proper = dai.value
                dai_val_proper_words = (tuple(dai_val_proper.split())
                                        if dai_val_proper else tuple())
                compatible_insts = (
                    lambda utt: utt.insts_for_typeval(dai_catlab_words,
                                                      dai_val_proper_words))
            # insts :: utt_id -> list of instatiations for dai_slot
            ab_types = [ot for ot in self.obss if ot.startswith('ab')]
            insts = {utt_id: reduce(
                     add, (compatible_insts(self.obss[ab_type][utt_id])
                           for ab_type in ab_types))
                     for utt_id in self.utt_ids}
            # all_insts = reduce(set.union, insts.itervalues(), set())
            feat_coords = (list(), list())
            feat_vals = list()
            outputs_orig = list()
            n_rows = 0
            for utt_id, utt_insts in insts.iteritems():
                if not utt_insts:
                    # Get the output (regressand).
                    outputs_orig.append(int(dai in self.das[utt_id]))
                    # Get the input (regressor).
                    utt_feats = self._extract_feats_from_one(
                        self.obss, utt_id=utt_id)
                    new_feat_coords, new_feat_vals = (
                        utt_feats.get_feature_coords_vals(self.feature_idxs))
                    feat_coords[0].extend(repeat(n_rows, len(new_feat_coords)))
                    feat_coords[1].extend(new_feat_coords)
                    feat_vals.extend(new_feat_vals)
                    n_rows += 1
                else:
                    for type_, value in utt_insts:
                        # Extract the outputs.
                        inst_dai = DialogueActItem(dai_dat, dai_slot,
                                                   ' '.join(value))
                        inst_dai.value2category_label(dai_catlab)
                        outputs_orig.append(int(inst_dai in self.das[utt_id]))
                        # Instantiate features for this type_=value assignment.
                        utt_feats = self._extract_feats_from_one(
                            self.obss, inst=(type_, value), utt_id=utt_id)
                        # Extract the inputs.
                        new_feat_coords, new_feat_vals = (
                            utt_feats.get_feature_coords_vals(
                                self.feature_idxs))
                        feat_coords[0].extend(repeat(n_rows,
                                                     len(new_feat_coords)))
                        feat_coords[1].extend(new_feat_coords)
                        feat_vals.extend(new_feat_vals)
                        n_rows += 1

            outputs_orig = np.array(outputs_orig, dtype=np.int8)
            # ...called outputs_orig to mark that they have not been balanced.

            # Check whether this DAI has sufficient count of in-/correct
            # occurrences.
            n_pos = np.sum(outputs_orig)
            n_neg = len(outputs_orig) - n_pos
            if verbose:
                msg = ("Support for training: {sup} (pos: {pos}, neg: {neg})"
                       .format(sup=len(outputs_orig), pos=n_pos, neg=n_neg))
                print msg
                print >>sys.stderr, msg
            if n_pos < min_correct_dai_count:
                if verbose:
                    print "...not enough positive examples"
                    print >>sys.stderr, "...not enough positive examples"
                    continue
            if n_neg < min_incorrect_dai_count:
                if verbose:
                    print "...not enough negative examples"
                    print >>sys.stderr, "...not enough negative examples"
                    continue

            # Prune features based on the selection of DAIs.
            # inputs = np.array(inputs, dtype=np.dtype(float)).transpose()
            # Create the transposed matrix first (rows indexed by features).
            # Enforce the right shape.
            feat_coords[0].append(0)
            feat_coords[1].append(len(self.feature_idxs) - 1)
            feat_vals.append(0)

            inputs_orig = csr_matrix(
                (feat_vals, (feat_coords[1], feat_coords[0])))
            # ...called inputs_orig to mark that they have not been balanced.
            n_feats_used = inputs_orig.shape[0]
            for feat_idx, feat_vec in enumerate(inputs_orig):
                n_occs = len(filter(
                    lambda feat_val: not (isnan(feat_val) or feat_val == 0),
                    (feat_vec[0, obs_idx]
                     for obs_idx in feat_vec.nonzero()[1])))
                # Test for minimal number of occurrences.
                if n_occs < min_feature_count:
                    # inputs_orig[feat_idx] = 0
                    for obs_idx in feat_vec.nonzero()[1]:
                        inputs_orig[feat_idx, obs_idx] = 0
                    n_feats_used -= 1
                else:
                    for obs_idx in feat_vec.nonzero()[1]:
                        orig_val = inputs_orig[feat_idx, obs_idx]
                        inputs_orig[feat_idx, obs_idx] = crop_to_finite(
                            orig_val)
            inputs_orig.eliminate_zeros()
            # Transpose inputs_orig back to the form with columns indexed by
            # features, rows by observations.
            inputs_orig = inputs_orig.transpose()
            if verbose:
                msg = ("Adaptively pruned features to {cnt}."
                       .format(cnt=n_feats_used))
                print msg
                print >>sys.stderr, msg
            if n_feats_used == 0:
                if verbose:
                    msg = "...no features, no training!"
                    print msg
                    print >>sys.stderr, msg
                continue

            # Balance the data.
            if balance:
                inputs, outputs = self.balance_data(inputs_orig, outputs_orig)
            else:
                inputs, outputs = inputs_orig, outputs_orig

            # Train and store the classifier for `dai'.
            try:
                if self.clser_type == 'logistic':
                    clser = LogisticRegression('l1', C=sparsification,
                                               tol=1e-6, class_weight='auto')
                    clser.fit(inputs, outputs)
                    # Save only the classifier's coefficients.
                    self.trained_classifiers[dai] = None  # to mark there IS
                                                        # a clser for this DAI
                    self.intercepts[dai] = clser.intercept_[0]
                    self.coefs[dai] = clser.coef_[0, :]
                else:
                    assert self.clser_type == 'tree'
                    inputs = inputs.toarray()  # dense format required by the
                                               # decision tree classifier
                    # TODO Make the parameters tunable.
                    clser = tree.DecisionTreeClassifier(min_samples_split=5,
                                                        max_depth=4)
                    clser.fit(inputs, outputs)
                    self.trained_classifiers[dai] = clser
            except:
                if verbose:
                    msg = "...not enough training data."
                    print msg
                    print >>sys.stderr, msg
                continue

            # Calibrate the prior.
            if calibrate:
                if verbose:
                    print >>sys.stderr, "Calibrating the prior..."
                calib_data = np.array([
                    (clser.predict_proba(feats)[0][1], output)
                    for (feats, output) in izip(inputs_orig, outputs_orig)])
                self._calibrate_prior(calib_data, dai, verbose=verbose)

            # after message
            if verbose:
                # Count non-zero features.
                if self.clser_type == 'logistic':
                    n_nonzero = np.count_nonzero(clser.coef_)
                    coefs_abs_sum += map(abs, clser.coef_)
                else:
                    n_nonzero = clser.tree_.node_count
                    coefs_abs_sum += clser.tree_.node_count
                # Count basic metrics.
                accuracy = clser.score(inputs, outputs)
                if self.clser_type == 'tree':
                    # Tree requires dense format.
                    predictions = [clser.predict(obs)[0] for obs in inputs]
                else:
                    predictions = [clser.predict(obs)[0]
                                   for obs in csr_matrix(inputs)]
                precision = metrics.precision_score(predictions, outputs)
                recall = metrics.recall_score(predictions, outputs)
                if precision * recall == 0.:
                    f_score = 0.
                else:
                    f_score = 2 * precision * recall / (precision + recall)
                # Print the message.
                msg = ("Accuracy for training data: {acc:6.2f} %\n"
                       "P/R/F: {p:.3f}/{r:.3f}/{f:.3f}\n"
                       # "Size of the params: {parsize}\n"
                       "Number of non-zero params: {nonzero}").format(
                           acc=(100 * accuracy),
                           p=precision,
                           r=recall,
                           f=f_score,
                           # parsize=clser.coef_.shape,
                           nonzero=n_nonzero)
                print msg
                # Print the non-zero features learned.
                if self.clser_type == 'logistic':
                    try:
                        nonzero_idxs = clser.coef_.nonzero()[1]
                    except:
                        nonzero_idxs = []
                    # [0] is intercept, perhaps
                    if len(nonzero_idxs):
                        print "Non-zero features:"
                        feat_tups = list()
                        for feat_idx in nonzero_idxs:
                            feat_weights = [coefs[feat_idx]
                                            for coefs in clser.coef_]
                            feat_str = Features.do_with_abstract(
                                self.idx2feature[feat_idx], str)
                            feat_tups.append((feat_weights, feat_str))
                        for feat_weights, feat_str in sorted(
                                feat_tups,
                                key=lambda item: -sum(map(abs, item[0]))):
                            weight_str = ' '.join('{w: >8.2f}'.format(w=weight)
                                                  for weight in feat_weights)
                            print "{w}  {f}".format(w=weight_str, f=feat_str)
                elif self.clser_type == 'tree':
                    nonzero_idxs = get_features_from_tree(clser)
                    if len(nonzero_idxs):
                        print "Non-zero features:"
                        # XXX The call to do_with_abstract should probably be
                        # removed.
                        for feat_idx in nonzero_idxs:
                            feat_str = Features.do_with_abstract(
                                self.idx2feature[feat_idx], str)
                            print feat_str
                print

        if verbose:
            print >>sys.stderr, "Done training."
            print "Total number of non-zero params:", \
                  np.count_nonzero(coefs_abs_sum)

        # # Calibrate the prior.
        # if calibrate and calib_data:
            # if verbose:
                # print >>sys.stderr, "Calibrating the prior..."
            # self._calibrate_prior(calib_data, verbose=verbose)

    def _calibrate_prior(self, calib_data, dai, exp_unknown=0.05,
                         verbose=False):
        """
        Calibrates the prior on classification (its bias).  Requires that the
        model be already trained.

        Arguments:
            calib_data: list of tuples (predicted probability, true label) for
                all classification examples
            dai: the DAI for whose classifier prior is being calibrated
            exp_unknown: expected answer for DAIs that are not labeled in
                training data.  This needs to be a float between 0.  and 1.,
                expressing how likely it is for such DAIs to be actually
                correct.
            verbose: Be verbose; if `verbose' > 1, produces a lot of output.
                For debugging purposes.

        """
        def fscore():
            if true_pos + false_pos:
                precision = true_pos / (true_pos + false_pos)
            else:
                precision = 0.
            if true_pos + false_neg:
                recall = true_pos / (true_pos + false_neg)
            else:
                recall = 0.
            if precision + recall > 0.:
                return 2 * precision * recall / (precision + recall)
            return 0.

        # Find the optimal decision boundary.
        # Here we use the absolute error, not squared error.  This should be
        # more efficient and have little impact on the result.
        calib_data = sorted(calib_data, key=itemgetter(0))
        calib_data = np.array(calib_data)
        true_pos = np.sum(calib_data, axis=0)[1]
        false_pos = np.sum(1. - calib_data, axis=0)[1]
        false_neg = 0.
        error = 1. - fscore()
        split_idx = 0
        best_error = error
        if verbose:
            print "Total error: {err}".format(err=error)
        datum_idx = 0
        while True:
            if verbose > 1:
                start_idx = datum_idx
            try:
                predicted, true = calib_data[datum_idx]
            except IndexError:
                break
            # Collect all the classifications for the same predicted value.
            point_cnt = 1
            point_cls_sum = true
            while True:
                try:
                    next_is_same = (calib_data[datum_idx + 1][0] == predicted)
                except IndexError:
                    break
                if next_is_same:
                    datum_idx += 1
                    point_cnt += 1
                    point_cls_sum += calib_data[datum_idx][1]
                else:
                    break
            # Compute the difference in total error.
            true_pos -= point_cls_sum
            false_pos -= point_cnt - point_cls_sum
            false_neg += point_cls_sum
            error = 1. - fscore()
            if error < best_error:
                best_error = error
                split_idx = datum_idx
            datum_idx += 1
            if verbose > 1:
                print "Split [{start}, {end}): pred={pred}, err={err}".format(
                    start=start_idx, end=datum_idx, pred=predicted, err=error)

        try:
            self.cls_thresholds[dai] = .5 * (calib_data[split_idx][0]
                                             + calib_data[split_idx + 1][0])
        except IndexError:
            self.cls_thresholds[dai] = calib_data[split_idx][0]

        if verbose:
            print
            print "Best error: {err}".format(err=best_error)
            print "Threshold: {thresh}".format(thresh=self.cls_thresholds[dai])
            print >>sys.stderr, "Done calibrating the prior."

    def forget_useless_feats(self):
        # Only implemented for the 'logistic' type of classifier.
        if self.clser_type == 'logistic':
            # Find feature indices actually used by classifiers.
            # as a set:
            # (the `[0]' selects the 0-th output variable, which is the only
            # one)
            used_fidxs = reduce(set.union, (set(coefs.nonzero()[0])
                                            for coefs in self.coefs.values()))
            # as an array:
            used_fidxs_ar = np.array(sorted(used_fidxs))
            # Map old feature indices onto new indices.
            fidx2new = dict((idx, order)
                            for (order, idx) in enumerate(used_fidxs_ar))

            # Use the mappings to update feature indexing structures.
            self.feature_idxs = dict((feat, fidx2new[fidx]) for (feat, fidx)
                                     in self.feature_idxs.iteritems()
                                     if fidx in used_fidxs)
            self.coefs = dict((dai, coefs[used_fidxs_ar])
                              for (dai, coefs) in self.coefs.iteritems())

    def save_model(self, file_name, do_reduce=True, gzip=None):
        """
        Exports the SLU model (obtained either from training or loaded).

        Arguments:
            file_name -- path to the file where to save the model
            do_reduce -- should features that don't influence the classifiers'
                         decisions be removed? (default: True)
            gzip -- should the model be saved gzipped? If set to None, this is
                    determined based on the `file_name':
                        gzip = file_name.endswith('gz')
                    (default: None)

        """
        if do_reduce:
            self.forget_useless_feats()
        if gzip is None:
            gzip = file_name.endswith('gz')
        version = '5'
        if self.clser_type == 'logistic':
            clser_data = (self.intercepts, self.coefs)
        else:
            clser_data = (self.trained_classifiers, )
        data = ((self.feature_idxs,
                 self.clser_type)
                + clser_data +
                (self.features_type,
                 # self.features_size,
                 self.ft_args,
                 self.ft_kwargs,
                 dict(self.cls_thresholds),
                 self.abstractions))
        if gzip:
            import gzip
            open_meth = gzip.open
        else:
            open_meth = open
        with open_meth(file_name, 'wb') as outfile:
            pickle.dump((version, data), outfile)

    def load_model(self, file_name):
        # Handle gzipped files.
        if file_name.endswith('gz'):
            import gzip
            open_meth = gzip.open
        else:
            open_meth = open

        with open_meth(file_name, 'rb') as infile:
            data = pickle.load(infile)
            if isinstance(data[0], basestring):
                version = data[0]
                data = data[1]
            else:
                version = '0'

        # For the new version,
        if version == '5':
            (self.feature_idxs, self.clser_type) = data[:2]
            if self.clser_type == 'logistic':
                (self.intercepts, self.coefs) = data[2:4]
                self.trained_classifiers = {dai: None for dai in self.coefs}
                next_idx = 4
            else:
                self.trained_classifiers = data[2]
                next_idx = 3
            (self.features_type, self.ft_args, self.ft_kwargs,
             cls_thresholds_dict, self.abstractions) = data[next_idx:]
            # Interpret cls_thresholds_dict as a defaultdict of thresholds for
            # all classifiers.
            self.cls_thresholds = defaultdict(lambda: 0.5)
            self.cls_thresholds.update(cls_thresholds_dict)
            self.cls_threshold = 0.5
        # For earlier versions:
        else:
            if version == '0':
                (self.features_list, self.feature_idxs,
                 self.trained_classifiers, self.features_type,
                 self.features_size) = data
            elif version == '1':
                (self.features_list, self.feature_idxs,
                 self.trained_classifiers, self.features_type,
                 self.features_size, self.cls_threshold) = data
            elif version == '2':
                (self.features_list, self.feature_idxs,
                 self.clser_type, self.trained_classifiers, self.features_type,
                 self.features_size, self.cls_threshold) = data
            elif version.startswith('3.') or version.startswith('DSTC13'):
                if version == 'DSTC13':
                    (self.features_list, self.feature_idxs,
                     self.clser_type, self.trained_classifiers,
                     self.features_type, self.features_size,
                     self.cls_threshold, self.abstractions) = data
                elif version in ('DSTC13.2', '3.0', '3.1'):
                    (self.feature_idxs,
                     self.clser_type, self.trained_classifiers,
                     self.features_type, self.features_size,
                     self.cls_threshold, self.abstractions) = data
                    if version == '3.1':
                        # Interpret self.cls_threshold as actually a dict of
                        # thresholds for all classifiers.
                        self.cls_thresholds = defaultdict(lambda: 0.5)
                        self.cls_thresholds.update(self.cls_threshold)
                        self.cls_threshold = 0.5
                if 'partial' in self.abstractions:
                    self._do_abstract_values.add(False)
                if 'abstract' in self.abstractions:
                    self._do_abstract_values.add(True)
            elif version == '4':
                (self.feature_idxs, self.clser_type) = data[:2]
                if self.clser_type == 'logistic':
                    (self.intercepts, self.coefs) = data[2:4]
                    self.trained_classifiers = {dai: None
                                                for dai in self.coefs}
                    next_idx = 4
                else:
                    self.trained_classifiers = data[2]
                    next_idx = 3
                (self.features_type, self.features_size, cls_thresholds_dict,
                 self.abstractions) = data[next_idx:]
                # Interpret cls_thresholds_dict as a defaultdict of thresholds
                # for all classifiers.
                self.cls_thresholds = defaultdict(lambda: 0.5)
                self.cls_thresholds.update(cls_thresholds_dict)
                self.cls_threshold = 0.5
            else:
                raise SLUException('Unknown version of the SLU model file: '
                                   '{v}.'.format(v=version))

            # Use default ft_args, ft_kwargs (new in version 5).
            self.ft_args = base.ft_default_args
            self.ft_kwargs = base.ft_default_kwargs

        # Recast model parameters from an sklearn object as plain lists of
        # coefficients and intercept.
        if version not in '45' and self.clser_type == 'logistic':
            self.intercepts = {
                dai: self.trained_classifiers[dai].intercept_[0]
                for dai in self.trained_classifiers}
            self.coefs = {dai: self.trained_classifiers[dai].coef_[0, :]
                          for dai in self.trained_classifiers}
            self.trained_classifiers = {dai: None for dai in self.coefs}

    def get_size(self):
        """Returns the number of features in use."""
        return len(self.features_idxs)

    @classmethod
    def _get_dais_for_normvalue(cls, da_nblist, dat, slot, value):
        # Substitute the original, unnormalised values back in the input DA
        # n-best list.
        act_dais = set(dai
                       for da in map(itemgetter(1), da_nblist)
                       for dai in da if dai.value == value)
        unnorm_values = list(reduce(
            set.union,
            (dai.unnorm_values for dai in act_dais),
            set()))
        # assert unnorm_values
        # Be robust.
        if not unnorm_values:
            return DialogueActItem(dat, slot, value)

        inst_dai = DialogueActItem(dat, slot, unnorm_values[0])
        for unnorm in unnorm_values[1:]:
            inst_dai.value2normalised(unnorm)
        # Let the true normalised value be the face value
        inst_dai.value2normalised(value)
        return inst_dai

    def predict_prob(self, dai, feat_vec):
        if self.clser_type == 'logistic':
            exponent = (-self.intercepts[dai]
                        - np.dot(self.coefs[dai], feat_vec))
            return 1. / (1. + np.exp(exponent))
        else:
            return self.trained_classifiers[dai].predict_proba(feat_vec)

    def parse_1_best(self, obs, ret_cl_map=False, include_other=True,
                     prob_combine_meth='max', verbose=False):
        """
        TODO Update.

        Parses `utterance' and generates the best interpretation in the form
        of a confusion network of dialogue acts.

        Arguments:
            utterance: an instance of Utterance or UtteranceHyp to be parsed
            prev_da: the immediately preceding DA if applicable; this is used
                     only if the model was trained using this information
                     (default: None)
            utt_nblist: mapping { utterance ID: utterance n-best list }, with
                 the utterance n-best list reflecting the ASR output
                 (default: None)
            da_nblist: mapping { utterance ID: DA n-best list }, with the DA
                 n-best list reflecting an SLU output
                 (default: None)
            ret_cl_map: whether the tuple (da_confnet, cl2vals_forms) should be
                        returned instead of just da_confnet.  The second member
                        of the tuple will be a mapping from category labels
                        identified in the utterance to the pair (slot value,
                        surface form).  (The slot name can be parsed from the
                        category label itself.)
            include_other -- include "other"-valued DAIs in the output confnet
            prob_combine_meth: be one of {'new', 'max', 'add', 'arit', 'harm'},
                and determines how probabilities for the same DAI from
                different classifiers should be merged (default: 'max')
            verbose: print debugging output?  More output is printed if
                     verbose > 1.


        """
        # Precondition checking.
        if not hasattr(self, 'feature_idxs'):
            raise DAILRException('Attempted to use the SLU parser without '
                                 'a model.')

        obs = copy.deepcopy(obs)

        if 'utt' in obs and isinstance(obs['utt'], UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            obs['utt'] = obs['utt'].utterance

        if 'utt' in obs and verbose:
            print 'Parsing utterance "{utt}".'.format(utt=obs['utt'])

        category_labels = dict()
        if self.preprocessing:
            abstractables = [obs_type
                             for obs_type in ('utt', 'utt_nbl', 'utt_cn')
                             if obs_type in obs]
            for concrete_ot in abstractables:
                abs_ot = 'ab' + concrete_ot
                obs[concrete_ot] = self.preprocessing.normalise(
                    obs[concrete_ot])
                obs[abs_ot], catlabs = (
                    self.preprocessing.values2catlabs(obs[concrete_ot]))
                # XXX Not sure whether any key in the dictionary can hereby get
                # rewritten and whether that would be wrong.  Not sure about
                # rewriting DAs in the above assignment, either.
                category_labels.update(catlabs)
                if verbose:
                    print 'After preprocessing ({cot}): "{utt}".'.format(
                        cot=concrete_ot, utt=obs[abs_ot])
            if verbose:
                print category_labels
        else:
            abstractables = tuple()
            category_labels = dict()

        # Generate utterance features.
        utterance_features = self._extract_feats_from_one(obs)
        conc_feat_vec = (utterance_features.get_feature_vector(
                         self.feature_idxs))

        if verbose >= 2:
            print 'Features: '
            for feature in utterance_features:
                print feature

        da_confnet = DialogueActConfusionNetwork()

        # Try all classifiers we have trained, not only those represented in
        # the input da_nblist (when classifying by DA n-best lists).
        for dai in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", dai

            dai_dat = dai.dat
            dai_slot = dai.name
            dai_catlab = dai.value
            dai_catlab_words = (tuple(dai_catlab.split()) if dai_catlab
                                else tuple())
            if dai.is_generic:
                compatible_insts = (lambda utt:
                                    utt.insts_for_type(dai_catlab_words))
            else:
                try:
                    dai_val_proper = next(iter(dai.orig_values))
                except StopIteration:
                    dai_val_proper = None
                dai_val_proper_words = (tuple(dai_val_proper.split())
                                        if dai_val_proper else tuple())
                compatible_insts = (
                    lambda utt: utt.insts_for_typeval(dai_catlab_words,
                                                      dai_val_proper_words))

            if abstractables:
                insts = reduce(add, (compatible_insts(obs['ab' + concrete_ot])
                                     for concrete_ot in abstractables))
            else:
                insts = None

            if insts:
                for type_, value in insts:
                    if not include_other and ' '.join(value) == dai.other_val:
                        continue
                    # Extract the inputs, instatiated for this type_=value
                    # assignment.
                    inst_feats = self._extract_feats_from_one(
                        obs, inst=(type_, value))
                    feat_vec = inst_feats.get_feature_vector(self.feature_idxs)
                    if verbose >= 2:
                        print 'Features*: '
                        for feature in inst_feats:
                            print feature

                    try:
                        dai_prob = self.predict_prob(dai, feat_vec)
                    except Exception as ex:
                        print '(EE) Parsing exception: ', ex
                        continue

                    if verbose:
                        print "Classification result: ", dai_prob

                    inst_dai = DialogueActItem(dai_dat, dai_slot,
                                               ' '.join(value))
                    # Not strictly needed, but this information is easy to
                    # obtain now.
                    inst_dai.value2category_label(dai_catlab)
                    # TODO Parameterise with the merging method.
                    da_confnet.add_merge(dai_prob, inst_dai,
                                         combine=prob_combine_meth)
                                         # overwriting=not dai.is_generic)
            else:
                if dai.is_generic or (not include_other
                                      and dai.other_val in dai.unnorm_values):
                    # Cannot evaluate an abstract classifier with no
                    # instantiations for its slot on the input.
                    continue
                try:
                    dai_prob = self.predict_prob(dai, conc_feat_vec)
                except Exception as ex:
                    print '(EE) Parsing exception: ', ex
                    continue

                if verbose:
                    print "Classification result: ", dai_prob

                da_confnet.add_merge(dai_prob, dai, combine=prob_combine_meth)

        if verbose:
            print "DA: ", da_confnet

        if self.preprocessing is not None:
            confnet = self.preprocessing.category_labels2values_in_dacn(
                da_confnet, category_labels)
            confnet.sort()
        else:
            confnet = da_confnet

        # DSTC relic.
        # Add DAs for which we have no classifiers, to the confnet with their
        # DAs' original probs.
        if 'da_nbl' in obs:
            for prob, da in obs['da_nbl']:
                for dai in da:
                    if dai not in confnet:
                        confnet.add(prob, dai)

        if ret_cl_map:
            return confnet, category_labels
        return confnet

    def parse_nblist(self, obs_list):
        """
        Parse n-best list by parsing each item in the list and then merging the
        results.

        """
        # XXX!!! Temporary workaround. However, this would be the way to handle
        # different types of observations in the new SLU parser (version >= 5).
        return self.parse_1_best(self, {'nbl_ngram': obs_list})

        if len(obs_list) == 0:
            return DialogueActConfusionNetwork()

        dacn_list = []
        for prob, utt in obs_list:
            if "__other__" == utt:
                dacn = DialogueActConfusionNetwork()
                dacn.add(1.0, DialogueActItem("other"))
            else:
                dacn = self.parse_1_best(utt)

            dacn_list.append((prob, dacn))

        dacn = merge_slu_confnets(dacn_list)
        dacn.prune()
        dacn.sort()

        return dacn

    def parse_confnet(self, confnet, include_other=True,
                      prob_combine_meth='max', verbose=False):
        """
        Parse the confusion network by generating an n-best list and parsing
        this n-best list.

        Arguments:
            confnet -- the utterance confnet to parse
            include_other -- include "other"-valued DAIs in the output confnet
            prob_combine_meth: be one of {'new', 'max', 'add', 'arit', 'harm'},
                and determines how probabilities for the same DAI from
                different classifiers should be merged (default: 'max')
            verbose -- print lots of output

        """
        # XXX!!! Temporary workaround. However, this would be the way to handle
        # different types of observations in the new SLU parser (version >= 5).
        return self.parse_1_best(self, {'cn_ngram': confnet},
                                 include_other=include_other,
                                 prob_combine_meth=prob_combine_meth,
                                 verbose=verbose)

        # Precondition checking.
        if not hasattr(self, 'feature_idxs'):
            raise DAILRException('Attempted to use the SLU parser without '
                                 'a model.')

        if verbose:
            print 'Parsing confnet "{cn}".'.format(cn=confnet)

        if self.preprocessing:
            confnet = self.preprocessing.normalise_confnet(confnet)
            ab_confnet, catlabs = (
                self.preprocessing.values2category_labels_in_confnet(confnet))
        # else:
            # catlabs = dict()

        # Generate utterance features.
        cn_feats = self._extract_feats_from_one(utt_hyp=confnet,
                                                abutt_hyp=ab_confnet)
        conc_feat_vec = (cn_feats.get_feature_vector(self.feature_idxs))

        if verbose >= 2:
            print 'Features: ', cn_feats

        da_confnet = DialogueActConfusionNetwork()

        # Try all classifiers we have trained, not only those represented in
        # the input da_nblist (when classifying by DA n-best lists).
        for dai in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", dai

            # TODO Pull out.
            dai_dat = dai.dat
            dai_slot = dai.name
            dai_catlab = dai.value
            dai_catlab_words = (tuple(dai_catlab.split()) if dai_catlab
                                else tuple())
            if dai.is_generic:
                compatible_insts = (lambda confnet:
                                    confnet.insts_for_type(dai_catlab_words))
            else:
                try:
                    dai_val_proper = next(iter(dai.orig_values))
                except StopIteration:
                    dai_val_proper = None
                dai_val_proper_words = (tuple(dai_val_proper.split())
                                        if dai_val_proper else tuple())
                compatible_insts = (
                    lambda confnet: confnet.insts_for_typeval(
                        dai_catlab_words, dai_val_proper_words))

            insts = compatible_insts(ab_confnet)

            if insts:
                for type_, value in insts:
                    if not include_other and ' '.join(value) == dai.other_val:
                        continue
                    # Extract the inputs, instatiated for this type_=value
                    # assignment.
                    inst_feats = self._extract_feats_from_one(
                        utt_hyp=confnet, abutt_hyp=ab_confnet,
                        inst=(type_, value))
                    feat_vec = inst_feats.get_feature_vector(self.feature_idxs)

                    try:
                        dai_prob = self.predict_prob(dai, feat_vec)
                        # dai_prob = (self.trained_classifiers[dai]
                                    # .predict_proba(feat_vec))
                    except Exception as ex:
                        print '(EE) Parsing exception: ', str(ex)
                        continue

                    if verbose:
                        print "Classification result: ", dai_prob

                    inst_dai = DialogueActItem(dai_dat, dai_slot,
                                               ' '.join(value))
                    # TODO Parameterise with the merging method.
                    da_confnet.add_merge(dai_prob, inst_dai,
                                         combine=prob_combine_meth)
                                         # overwriting=not dai.is_generic)
            else:
                if dai.is_generic or (not include_other
                                      and dai.other_val in dai.unnorm_values):
                    # Cannot evaluate an abstract classifier with no
                    # instantiations for its slot on the input.
                    continue
                try:
                    dai_prob = self.predict_prob(dai, conc_feat_vec)
                    # dai_prob = (self.trained_classifiers[dai]
                                # .predict_proba(conc_feat_vec))
                except Exception as ex:
                    print '(EE) Parsing exception: ', str(ex)
                    continue

                if verbose:
                    print "Classification result: ", dai_prob

                dai.category_label2value()
                da_confnet.add_merge(dai_prob, dai,
                                     combine=prob_combine_meth)

        if verbose:
            print "DA: ", da_confnet

        return da_confnet
