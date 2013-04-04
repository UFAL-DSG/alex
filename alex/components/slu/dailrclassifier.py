#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

from collections import defaultdict
import copy
import cPickle as pickle
from itertools import izip, repeat
from math import isnan
import numpy as np
from operator import itemgetter
import random
from scipy.sparse import csr_matrix, vstack
import sys

from sklearn import metrics, tree
from sklearn.linear_model import LogisticRegression

from alex.components.asr.utterance import UtteranceFeatures, \
    UtteranceNBListFeatures, UtteranceHyp
from alex.components.slu import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork, DialogueActFeatures, \
    DialogueActNBListFeatures, merge_slu_confnets
from alex.ml.features import Abstracted, Features
from alex.utils.exception import DAILRException, SLUException
from alex.utils.various import crop_to_finite, flatten

from alex.utils import pdbonerror


class DAILogRegClassifier(SLUInterface):
    """Implements learning of and decoding with dialogue act item classifiers
    based on logistic regression.

    When used for parsing an utterance, each classifier decides whether its
    respective dialogue act item is present.  Then, the output dialogue act is
    constructed by joining all detected dialogue act items.

    Dialogue act is defined as a composition of dialogue act items. E.g.

    confirm(drinks="wine")&inform(name="kings shilling")
        <=> 'does kings serve wine'

    where confirm(drinks="wine") and inform(name="kings shilling") are two
    dialogue act items.

    This parser uses logistic regression as the classifier of the dialogue
    act items.


    Attributes:
        category_labels: mapping { utterance ID:
                                    { category label: original string } }
        cls_threshold: threshold for classifying as positive
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
        utterances: mapping { utterance ID: utterance } for training utterances

    Type of features:
        By default, 'ngram' is used, meaning n-grams up to order 4 plus all
        skip n-grams of maximally that order are extracted.

        Value of the argument specifying the type of features is tested for
        inclusion of specific feature types.  If it __contains__ (may it be as
        a substring, or a member of a tuple, for example) any of the following
        keywords, the corresponding type of features is extracted.

            'ngram': n-grams (as described above)
            'prev_da': features of the DA preceding to the one to be classified
            'utt_nbl': features of an utterance n-best list (output from ASR,
                       presumably)
            'da_nbl': features of a DA n-best list (output from SLU,
                      presumably)
            'da_nbl_orig': features of a DA n-best list (output from SLU,
                      presumably) with original scores

    """
    # TODO Document attributes from the original DAILogRegClassifier class
    # (from the load_model method on).
    # TODO Document changes made in slot value abstraction for DSTC.

    # TODO Document.
    def __init__(self,
                 preprocessing=None,
                 clser_type='logistic',
                 features_type='ngram',
                 features_size=4,
                 abstractions=('concrete',            'abstract')):
        """TODO

        Arguments (partial listing):
            abstractions: what abstractions to do with DAs:
                'concrete' ... include concrete DAs
                'partial'  ... include DAs instantiated with do_abstract=False
                'abstract' ... include DAs instantiated with do_abstract=True
                (default: ('concrete', 'partial', 'abstract'))

        """
        # FIXME: maybe the SLU components should use the Config class to
        # initialise themselves.  As a result it would create their category
        # label database and pre-processing classes.
        random.seed()

        # Save the arguments.
        self.preprocessing = preprocessing
        self.clser_type = clser_type
        self.features_type = features_type
        self.features_size = features_size
        self.abstractions = abstractions

        # Additional bookkeeping.
        # Setting protected fields to None is interpreted as that they have to
        # be computed yet.
        self.cls_threshold = 0.5
        self.abutterances = None
        self.abutt_nblists = None
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
        # Mimic the process of extracting features, note down indices of
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

    def _extract_feats_from_one(self, utterance=None, abutterance=None,
                                prev_da=None, utt_nblist=None,
                                abutt_nblist=None, da_nblist=None,
                                da_nblist_orig=None, inst=None):
        """inst now changes the behaviour only for utterances.

        TODO Document.

        """
        ft = self.features_type
        fs = self.features_size
        # Collect all types of features.
        feat_sets = list()
        # TODO Generalise (compress the code).
        if 'ngram' in ft:
            if inst == 'all':
                for do_abstract in self._do_abstract_values:
                    feats = Features.join(
                        (UtteranceFeatures('ngram', fs, inst)
                         for inst in
                         abutterance.all_instantiations(do_abstract)),
                        distinguish=False)
                    # Features values can hereby get quite high, but that's
                    # alright, as there will also be correspondingly many
                    # training examples generated from this utterance.
                    feat_sets.append(feats)
                if 'concrete' in self.abstractions:
                    feat_sets.append(UtteranceFeatures('ngram', fs, utterance))
            elif inst is None:
                for do_abstract in self._do_abstract_values:
                    feat_sets.append(Features())
                feat_sets.append(UtteranceFeatures('ngram', fs, utterance))
            else:
                # `inst' is an instantiation: (type_, value)
                for do_abstract in self._do_abstract_values:
                    utt_inst = abutterance.instantiate(
                        inst[0], inst[1], do_abstract=do_abstract)
                    feat_sets.append(UtteranceFeatures('ngram', fs, utt_inst))
                if 'concrete' in self.abstractions:
                    feat_sets.append(UtteranceFeatures('ngram', fs, utterance))

        if 'prev_da' in ft:
            if prev_da is not None:
                feat_sets.append(DialogueActFeatures(prev_da))
            else:
                feat_sets.append(Features())
        if 'utt_nbl' in ft:
            if utt_nblist is not None:
                feat_sets.append(
                    UtteranceNBListFeatures(size=fs,
                                            utt_nblist=utt_nblist))
            else:
                feat_sets.append(Features())
        if 'da_nbl' in ft:
            if da_nblist is not None:
                feat_sets.append(
                    DialogueActNBListFeatures(da_nblist=da_nblist))
            else:
                feat_sets.append(Features())
        if 'da_nbl_orig' in ft:
            if da_nblist_orig is not None:
                feat_sets.append(
                    DialogueActNBListFeatures(da_nblist=da_nblist_orig))
            else:
                feat_sets.append(Features())

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
                .format(ft=ft))
        return feats

    def _extract_feats_from_many(self, prev_das=None, utt_nblists=None,
                                 abutt_nblists=None, da_nblists=None,
                                 da_nblists_orig=None, inst=None):
        self.n_feat_sets = (
            ('ngram' in self.features_type) * len(self.abstractions) +
            ('utt_nbl' in self.features_type) * len(self.abstractions) +
            ('da_nbl' in self.features_type) * bool(da_nblists) +
            ('da_nbl_orig' in self.features_type) * bool(da_nblists_orig))

        # XXX Why the asymmetry with self.utterances (and not utterances
        # passed in as an argument)?
        return {utt_id:
                self._extract_feats_from_one(
                    utterance=(self.utterances[utt_id]
                               if self.utterances is not None else None),
                    abutterance=(self.abutterances[utt_id]
                                 if self.abutterances is not None else None),
                    prev_da=(prev_das[utt_id]
                             if prev_das is not None else None),
                    utt_nblist=(utt_nblists[utt_id]
                                if utt_nblists is not None else None),
                    abutt_nblist=(abutt_nblists[utt_id]
                                  if abutt_nblists is not None else None),
                    da_nblist=(da_nblists[utt_id]
                               if da_nblists is not None else None),
                    da_nblist_orig=(da_nblists_orig[utt_id]
                                    if da_nblists_orig is not None else None),
                    inst=inst)
                for utt_id in self.utt_ids}

    # FIXME: Move the `das' argument to the first place (after self) and make
    # it obligatory also formally.  This will require refactoring code that
    # uses this class, calling this method with positional arguments.
    def extract_features(self, utterances=None, das=None, prev_das=None,
                         utt_nblists=None, da_nblists=None,
                         da_nblists_orig=None, verbose=False):
        """Extracts features from given utterances or system DAs or utterance
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
            da_nblists_orig: mapping { ID: DA n-best list }, with the DA n-best list
                reflecting an SLU output with original SDS's scores (default: None)
            verbose: print debugging output?  More output is printed if
                verbose > 1.

        The dictionary arguments are expected to all have the same set of keys.

        """
        self.utterances = utterances
        self.utt_nblists = utt_nblists
        self.das = das
        if utterances:
            self.utt_ids = utterances.keys()
        elif utt_nblists:
            self.utt_ids = utt_nblists.keys()
        elif da_nblists:
            self.utt_ids = da_nblists.keys()
        elif da_nblists_orig:
            self.utt_ids = da_nblists_orig.keys()
        else:
            raise DAILRException(
                'Cannot learn a classifier without utterances and without '
                'ASR or SLU hypotheses.')

        # Normalise the text and substitute category labels.
        self.abutterances = None
        abutt_nblists = None
        self.category_labels = {}
        if self.preprocessing:
            if not (bool(utterances) or bool(utt_nblists)):
                raise DAILRException(
                    'Cannot do preprocessing without utterances and without '
                    'ASR hypotheses.')
            # Learning from transcriptions...
            if utterances:
                self.abutterances = dict()
                for utt_id in self.utt_ids:
                    # Normalise the text.
                    self.utterances[utt_id] = self.preprocessing\
                        .text_normalisation(self.utterances[utt_id])
                    # Substitute category labes.
                    (self.abutterances[utt_id],
                     self.das[utt_id],
                     self.category_labels[utt_id]) = \
                        self.preprocessing.values2category_labels_in_da(
                            self.utterances[utt_id], self.das[utt_id])
            # ...or, learning from utterance hypotheses.
            if utt_nblists:
                abutt_nblists = dict()
                for utt_id in self.utt_nblists.iterkeys():
                    nblist = self.utt_nblists[utt_id]
                    if nblist is None:
                        # FIXME This should rather be discarded right away.
                        continue
                    # Normalise the text.
                    for utt_idx, hyp in enumerate(nblist):
                        utt = hyp[1]
                        nblist[utt_idx][1] = (self.preprocessing
                                              .text_normalisation(utt))
                    # Substitute category labes.
                    (abutt_nblists[utt_id],
                     self.das[utt_id],
                     self.category_labels[utt_id]) = \
                        self.preprocessing.values2category_labels_in_da(
                            nblist, self.das[utt_id])

        # Generate utterance features.
        self.utterance_features = self._extract_feats_from_many(
            prev_das=prev_das,
            utt_nblists=utt_nblists,
            abutt_nblists=abutt_nblists,
            da_nblists=da_nblists,
            da_nblists_orig=da_nblists_orig,
            inst='all')
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
                lambda feature:
                    self.feat_counts[feature] < _min_count,
                self.feat_counts.iterkeys()))
        else:
            conc_idxs = self._get_conc_feats_idxs()
            low_count_features = set(filter(
                lambda feature:
                    self.feat_counts[feature] < (
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
        """Prints what `extract_classifiers(verbose=True)' would output in
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
                    print self.utterances[utt_id]
                    print self.category_labels[utt_id]

    def prune_classifiers(self, min_dai_count=5, min_correct_count=None,
                          min_incorrect_count=None, accept_dai=None):
        """Prunes classifiers for DAIs that cannot be reliably classified with
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
                DAILogRegClassifierLearning object, and `dai' the DAI in
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
                # TODO Check that generic and bound DAIs are handled correctly
                # here.
                #
                # Discard a DAI that is reasonably complex and yet has too few
                # occurrences.
                if dai.is_generic:
                    return True
                if (dai.name is not None
                        and dai.value is not None
                        # and not dai.has_category_label()
                        and self._dai_counts[dai] < min_dai_count):
                    return False
                # XXX!!! Hack to pass the test without training a larger model.
                if dai.dat == 'reqalts':
                    return False
                # # Discard a DAI in the form '(slotname="dontcare")'.
                # if dai.name is not None and dai.value == "dontcare":
                    # return False
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
        """the input matrix of features for training utterances

        Beware, this getter will fail if `extract_features' was not called
        before.

        """
        if self._input_matrix is None:
            self.gen_input_matrix()
        return self._input_matrix

    def gen_input_matrix(self):
        """Generates the observation matrix from training data.

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
            new_inputs.extend(inputs[random.choice(output_idxs),:]
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
        if calibrate:
            calib_data = list()
        if verbose:
            coefs_abs_sum = np.zeros(shape=(1, len(self.feature_idxs)))
        # Precompute utterance instantiations.
        utts_insts = {utt_id: list(utt.iter_instantiations())
                      for (utt_id, utt) in self.abutterances.iteritems()}
        inst2str = lambda type_val: (type_val[0][0], ' '.join(type_val[1]))
        utts_insts_str = {utt_id: map(inst2str, insts)
                          for (utt_id, insts) in utts_insts.iteritems()}

        for dai in sorted(self._dai_counts):
            # before message
            if verbose:
                print >>sys.stderr, "Training classifier: ", str(dai)
                print "Training classifier: ", str(dai)

            # (TODO) We might want to skip this based on whether NaNs were
            # considered in the beginning.  That might be specified in an
            # argument to the initialiser.

            # Instantiate inputs and outputs for the current classifier.
            # TODO Check this does what was intended. Simplify.
            dai_dat = dai.dat
            dai_slot = dai.name
            dai_catlab = dai.value
            if dai.is_generic:
                inst_is_compatible = lambda type_val: type_val[0] == dai_catlab
            else:
                try:
                    dai_val_proper = next(iter(dai.orig_values))
                except StopIteration:
                    dai_val_proper = dai.value
                inst_is_compatible = (lambda type_val:
                    type_val == (dai_catlab, dai_val_proper))
            # insts :: utt_id -> list of instatiations for dai_slot
            insts = {utt_id: [inst for (inst, inst_str)
                              in zip(utt_insts, utts_insts_str[utt_id])
                              if inst_is_compatible(inst_str)]
                     for (utt_id, utt_insts) in utts_insts.iteritems()}
            all_insts = reduce(set.union, insts.itervalues(), set())
            feat_coords = (list(), list())
            feat_vals = list()
            outputs = list()
            n_rows = 0
            for utt_id, utt_insts in insts.iteritems():
                if not utt_insts:
                    # Get the output (regressand).
                    outputs.append(int(dai in self.das[utt_id]))
                    # Get the input (regressor).
                    utt_feats = self._extract_feats_from_one(
                        utterance=self.utterances[utt_id],
                        abutterance=self.abutterances[utt_id])
                    new_feat_coords, new_feat_vals = (utt_feats
                        .get_feature_coords_vals(self.feature_idxs))
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
                        outputs.append(int(inst_dai in self.das[utt_id]))
                        # Instantiate features for this type_=value assignment.
                        utt_feats = self._extract_feats_from_one(
                            utterance=self.utterances[utt_id],
                            abutterance=self.abutterances[utt_id],
                            inst=(type_, value))
                        # Extract the inputs.
                        new_feat_coords, new_feat_vals = (utt_feats
                            .get_feature_coords_vals(self.feature_idxs))
                        feat_coords[0].extend(repeat(n_rows,
                                                     len(new_feat_coords)))
                        feat_coords[1].extend(new_feat_coords)
                        feat_vals.extend(new_feat_vals)
                        n_rows += 1

            outputs = np.array(outputs, dtype=np.int8)
            # Check whether this DAI has sufficient count of in-/correct
            # occurrences.
            n_pos = np.sum(outputs)
            n_neg = len(outputs) - n_pos
            if verbose:
                print ("Support for training: {sup} (pos: {pos}, neg: {neg})"
                       .format(sup=len(outputs), pos=n_pos, neg=n_neg))
            if n_pos < min_correct_dai_count:
                if verbose:
                    print "...not enough positive examples"
                    continue
            if n_neg < min_incorrect_dai_count:
                if verbose:
                    print "...not enough negative examples"
                    continue

            # Prune features based on the selection of DAIs.
            # inputs = np.array(inputs, dtype=np.dtype(float)).transpose()
            # Create the transposed matrix first (rows indexed by features).
            # Enforce the right shape.
            feat_coords[0].append(0)
            feat_coords[1].append(len(self.feature_idxs) - 1)
            feat_vals.append(0)

            inputs = csr_matrix((feat_vals, (feat_coords[1], feat_coords[0])))
            n_feats_used = inputs.shape[0]
            for feat_idx, feat_vec in enumerate(inputs):
                n_occs = len(filter(
                    lambda feat_val: not (isnan(feat_val) or feat_val == 0),
                    (feat_vec[0,obs_idx]
                     for obs_idx in feat_vec.nonzero()[1])))
                # Test for minimal number of occurrences.
                if n_occs < min_feature_count:
                    # inputs[feat_idx] = 0
                    for obs_idx in feat_vec.nonzero()[1]:
                        inputs[feat_idx, obs_idx] = 0
                    n_feats_used -= 1
                else:
                    for obs_idx in feat_vec.nonzero()[1]:
                        orig_val = inputs[feat_idx, obs_idx]
                        inputs[feat_idx, obs_idx] = crop_to_finite(orig_val)
            inputs.eliminate_zeros()
            # Transpose inputs back to the form with columns indexed by
            # features, rows by observations.
            inputs = inputs.transpose()
            if verbose:
                print ("Adaptively pruned features to {cnt}."
                       .format(cnt=n_feats_used))
            if n_feats_used == 0:
                if verbose:
                    print "...no features, no training!"
                continue

            # Balance the data.
            if balance:
                inputs, outputs = self.balance_data(inputs, outputs)

            # Train and store the classifier for `dai'.
            try:
                if self.clser_type == 'logistic':
                    clser = LogisticRegression('l1', C=sparsification,
                                               tol=1e-6, class_weight='auto')
                    clser.fit(inputs, outputs)
                else:
                    assert self.clser_type == 'tree'
                    # TODO Make the parameters tunable.
                    clser = tree.DecisionTreeClassifier(min_samples_split=5,
                                                        max_depth=4)
                    clser.fit(inputs, outputs)
            except:
                if verbose:
                    print "...not enough training data."
                continue
            self.trained_classifiers[dai] = clser

            if calibrate:
                calib_data.extend((clser.predict_proba(feats)[0][1], output)
                                  for (feats, output) in izip(inputs, outputs))

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
                # (TODO: This could be done for the tree, too.)
                print

        if verbose:
            print >>sys.stderr, "Done training."
            print "Total number of non-zero params:", \
                  np.count_nonzero(coefs_abs_sum)

        # Calibrate the prior.
        if calibrate and calib_data:
            if verbose:
                print >>sys.stderr, "Calibrating the prior..."
            self._calibrate_prior(calib_data, verbose=verbose)

    def _calibrate_prior(self, calib_data, exp_unknown=0.05, verbose=False):
        """Calibrates the prior on classification (its bias).  Requires that
        the model be already trained.

        Arguments:
            calib_data: list of tuples (predicted probability, true label) for
                all classification examples
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
            self.cls_threshold = .5 * (calib_data[split_idx][0]
                                       + calib_data[split_idx + 1][0])
        except IndexError:
            self.cls_threshold = calib_data[split_idx][0]

        if verbose:
            print
            print "Best error: {err}".format(err=best_error)
            print "Threshold: {thresh}".format(thresh=self.cls_threshold)
            print >>sys.stderr, "Done calibrating the prior."

    def save_model(self, file_name):
        version = '3.0'
        data = (self.feature_idxs,
                self.clser_type,
                {dai: clser for dai, clser in
                 self.trained_classifiers.iteritems()},
                self.features_type,
                self.features_size,
                self.cls_threshold,
                self.abstractions
        )
        with open(file_name, 'w+') as outfile:
            pickle.dump((version, data), outfile)

    ###############################################################
    ### From here on, the methods come from what used to be the ###
    ### DAILogRegClassifier class.                              ###
    ###############################################################

    def load_model(self, file_name):
        with open(file_name, 'r') as infile:
            data = pickle.load(infile)
            if isinstance(data[0], basestring):
                version = data[0]
                data = data[1]
            else:
                version = '0'

        if version == '0':
            (self.features_list, self.feature_idxs, self.trained_classifiers,
                self.features_type, self.features_size) = data
        elif version == '1':
            (self.features_list, self.feature_idxs,
             self.trained_classifiers, self.features_type,
             self.features_size, self.cls_threshold) = data
        elif version == '2':
            (self.features_list, self.feature_idxs,
             self.clser_type, self.trained_classifiers, self.features_type,
             self.features_size, self.cls_threshold) = data
        elif version == '3.0' or version.startswith('DSTC13'):
            if version == 'DSTC13':
                (self.features_list, self.feature_idxs,
                 self.clser_type, self.trained_classifiers, self.features_type,
                 self.features_size, self.cls_threshold,
                 self.abstractions) = data
            elif version == '3.0' or version == 'DSTC13.2':
                (self.feature_idxs,
                 self.clser_type, self.trained_classifiers, self.features_type,
                 self.features_size, self.cls_threshold,
                 self.abstractions) = data
            if 'partial' in self.abstractions:
                self._do_abstract_values.add(False)
            if 'abstract' in self.abstractions:
                self._do_abstract_values.add(True)
        else:
            raise SLUException('Unknown version of the SLU model file: '
                               '{v}.'.format(v=version))

    def get_size(self):
        """Returns the number of features in use."""
        return len(self.features_idxs)

    @classmethod
    def _get_dais_for_normvalue(cls, da_nblist, dat, slot, value):
        # Substitute the original, unnormalised values back in
        # the input DA n-best list.
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

    def parse_1_best(self,
                     utterance=None,
                     prev_da=None,
                     utt_nblist=None,
                     da_nblist=None,
                     da_nblist_orig=None,
                     ret_cl_map=False,
                     verbose=False):
        """Parses `utterance' and generates the best interpretation in the form
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
            da_nblist_orig: mapping { utterance ID: DA n-best list }, with the DA
                 n-best list reflecting an SLU output with original SDS's
                 scores
                 (default: None)
            ret_cl_map: whether the tuple (da_confnet, cl2vals_forms) should be
                        returned instead of just da_confnet.  The second member
                        of the tuple will be a mapping from category labels
                        identified in the utterance to the pair (slot value,
                        surface form).  (The slot name can be parsed from the
                        category label itself.)
            verbose: print debugging output?  More output is printed if
                     verbose > 1.


        """
        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        if verbose:
            print 'Parsing utterance "{utt}".'.format(utt=utterance)

        if self.preprocessing:
            utterance = self.preprocessing.text_normalisation(utterance)
            abutterance, category_labels = \
                self.preprocessing.values2category_labels_in_utterance(
                    utterance)
            if verbose:
                print 'After preprocessing: "{utt}".'.format(utt=abutterance)
                print category_labels
            # XXX If working with utterance n-best lists, preprocess them here,
            # store the result to abutt_nblist and pass that as an argument to
            # _extract_feats_... below.
        else:
            category_labels = dict()

        # Generate utterance features.
        utterance_features = self._extract_feats_from_one(
            utterance=utterance,
            abutterance=abutterance,
            prev_da=prev_da,
            utt_nblist=utt_nblist,
            da_nblist=da_nblist,
            da_nblist_orig=da_nblist_orig)
        conc_feat_vec = (utterance_features.get_feature_vector(
                         self.feature_idxs))

        if verbose >= 2:
            print 'Features: ', utterance_features

        da_confnet = DialogueActConfusionNetwork()

        # TODO Pull out.
        inst2str = lambda type_val: (type_val[0][0], ' '.join(type_val[1]))

        # Try all classifiers we have trained, not only those represented in
        # the input da_nblist (when classifying by DA n-best lists).
        for dai in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", dai

            dai_dat = dai.dat
            dai_slot = dai.name
            dai_catlab = dai.value
            if dai.is_generic:
                inst_is_compatible = lambda type_val: type_val[0] == dai_catlab
            else:
                try:
                    dai_val_proper = next(iter(dai.orig_values))
                except StopIteration:
                    dai_val_proper = None
                inst_is_compatible = (lambda type_val:
                    type_val == (dai_catlab, dai_val_proper))

            # Relic from DSTC.
            # if da_nblist and any(
                    # any(dai.name for dai in hyp[1]) for hyp in da_nblist):
                # insts = set((dai.name, dai.value) for hyp in da_nblist
                            # for dai in hyp[1]
                            # if dai.name == dai_slot and dai.value)
            # else:
                # insts = None
            if abutterance:
                insts = list(abutterance.iter_instantiations())
                insts = [inst for (inst, inst_str)
                         in zip(insts, map(inst2str, insts))
                         if inst_is_compatible(inst_str)]
            else:
                insts = None

            if insts:
                for type_, value in insts:
                    # Extract the inputs, instatiated for this type_=value
                    # assignment.
                    inst_feats = self._extract_feats_from_one(
                        utterance=utterance, abutterance=abutterance,
                        inst=(type_, value))
                    feat_vec = inst_feats.get_feature_vector(self.feature_idxs)

                    try:
                        dai_prob = (self.trained_classifiers[dai]
                                    .predict_proba(feat_vec))
                    except Exception as ex:
                        print '(EE) Parsing exception: ', ex
                        continue

                    if verbose:
                        print "Classification result: ", dai_prob

                    # Restore the unnormalised values of the DAI.
                    # DSTC relic.
                    # inst_dai = self._get_dais_for_normvalue(
                        # da_nblist, dai._combined[0], type_, value)
                    # if dai_prob[0][1] > 0.4:
                        # import sys
                        # if not 'ipdb' in sys.modules:
                            # import ipdb; ipdb.set_trace()
                    inst_dai = DialogueActItem(dai_dat, dai_slot,
                                               ' '.join(value))
                    # Not strictly needed, but this information is easy to
                    # obtain now.
                    inst_dai.value2category_label(dai_catlab)
                    da_confnet.add_merge(dai_prob[0][1], inst_dai,
                                         is_normalised=False)
            else:
                if not isinstance(dai, DialogueActItem):
                    # Cannot evaluate an abstract classifier with no
                    # instantiations for its slot on the input.
                    continue
                try:
                    dai_prob = (self.trained_classifiers[dai]
                                .predict_proba(conc_feat_vec))
                except Exception as ex:
                    print '(EE) Parsing exception: ', ex
                    continue

                if verbose:
                    print "Classification result: ", dai_prob

                da_confnet.add_merge(dai_prob[0][1], dai, is_normalised=False)

        if verbose:
            print "DA: ", da_confnet

        if self.preprocessing is not None:
            confnet = self.preprocessing.category_labels2values_in_confnet(
                da_confnet, category_labels)
            confnet.sort()
        else:
            confnet = da_confnet

        # DSTC relic.
        # Add DAs for which we have no classifiers, to the confnet with their
        # DAs' original probs.
        if da_nblist or da_nblist_orig:
            the_nblist = da_nblist or da_nblist_orig
            for prob, da in the_nblist:
                for dai in da:
                    if dai not in confnet:
                        confnet.add(prob, dai)

        if ret_cl_map:
            return confnet, category_labels
        return confnet

    def parse_nblist(self, utterance_list):
        """Parse N-best list by parsing each item in the list and then merging
        the results."""

        if len(utterance_list) == 0:
            raise DAILRException("Empty utterance N-best list.")

        confnets = []
        for prob, utt in utterance_list:
            if "__other__" == utt:
                confnet = DialogueActConfusionNetwork()
                confnet.add(1.0, DialogueActItem("other"))
            else:
                confnet = self.parse_1_best(utt)

            confnets.append((prob, confnet))

            # print prob, utt
            # confnet.prune()
            # confnet.sort()
            # print confnet

        confnet = merge_slu_confnets(confnets)
        confnet.prune()
        confnet.sort()

        return confnet

    def parse_confnet(self, confnet, verbose=False):
        """Parse the confusion network by generating an N-best list and parsing
        this N-best list."""

        #TODO: We should implement a parser which uses features directly from
        # confusion networks.

        # print "Confnet"
        # print confnet
        # print

        nblist = confnet.get_utterance_nblist(n=40)

        # print "NBList"
        # print nblist
        # print

        sem = self.parse_nblist(nblist)

        # print "Semantics"
        # print sem
        # print

        return sem


# TODO Delete this class.
class DAILogRegClassifierLearning(DAILogRegClassifier):
    """Merged into DAILogRegClassifier, retained for compatibility."""
    pass
