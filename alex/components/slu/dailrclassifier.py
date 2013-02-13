#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

import numpy as np
import cPickle as pickle

from sklearn.linear_model import LogisticRegression

from alex.components.asr.utterance import UtteranceFeatures, UtteranceHyp
from alex.components.slu.__init__ import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork, merge_slu_confnets
from alex.utils.exception import DAILRException


class DAILogRegClassifierLearning(object):
    """Implements learning of dialogue act item classifiers based on logistic
    regression.

    Attributes:
        category_labels: mapping { utterance ID:
                                    { category label: original string } }
        dai_counts: mapping { str(DAI): number of occurrences in data }
        das: mapping { utterance ID: DA } for DAs corresponding to training
             utterances
        feat_counts: mapping { feature: number of occurrences }
        feature_idxs: mapping { feature: feature index }; feature indices span
                      range(0, number_of_features)
        features_size: size (order) of features, i.e., length of the n-grams
        features_type: type of features (only 'ngram' is supported now)
        input_matrix: observation matrix, a numpy array with rows corresponding
                      to utterances and columns corresponding to features
        output_matrix: mapping { str(DAI): [ utterance index: ?DAI
                                             present in utterance ] }
                       where the list is a numpy array, and the values are
                       either 0.0 or 1.0
        preprocessing: an SLUPreprocessing object to be used for preprocessing
                       of utterances and DAs
        trained_classifiers: mapping { DAI: classifier for this DAI }
        utterance_features: mapping { utterance ID: utterance features } where
                            the features is an UtteranceFeatures object
        utterances: mapping { utterance ID: utterance } for utterances to learn
                    from

    """

    def __init__(self,
                 preprocessing=None,
                 features_type='ngram',
                 features_size=4):
        # Save the arguments.
        self.features_type = features_type
        self.features_size = features_size
        self.preprocessing = preprocessing

        # Additional bookkeeping.
        # Setting protected fields to None is interpreted as that they have to
        # be computed yet.
        self._dai_counts = None
        self._input_matrix = None
        self._output_matrix = None

    def extract_features(self, utterances, das, verbose=False):
        """Extracts features from given utterances, making use of their
        corresponding DAs.  This is a pre-requisite to pruning features,
        classifiers, and running training with this learner.

        Arguments:
            utterances: mapping { utterance ID: utterance }, the utterance
                        being an instance of the Utterance class
            das: mapping { utterance ID: DA }, the DA being an instance of the
                 DialogueAct class

        The arguments are expected to have both the same set of keys.

        """
        self.utterances = utterances
        self.das = das

        # Normalise the text and substitute category labels.
        self.category_labels = {}
        if self.preprocessing:
            for utt_id in self.utterances.keys():
                self.utterances[utt_id] = self.preprocessing\
                    .text_normalisation(self.utterances[utt_id])
                self.utterances[utt_id], self.das[utt_id], \
                        self.category_labels[utt_id] = \
                    self.preprocessing.values2category_labels_in_da(
                        self.utterances[utt_id], self.das[utt_id])

        # Generate utterance features.
        ft = self.features_type
        fs = self.features_size
        uts = self.utterances
        self.utterance_features = \
            {utt_id: UtteranceFeatures(ft, fs, uts[utt_id])
             for utt_id in self.utterances}

    def prune_features(self, min_feature_count=5, verbose=False):
        """Prunes features that occur few times.

        Arguments:
            min_feature_count: minimum number of a feature occurring for it not
                               to be pruned (default: 5)
            verbose: whether to print diagnostic messages to
                               stdout (default: False)

        """
        # Count number of occurrences of features.
        self.feat_counts = dict()
        for utt_id in self.utterances.keys():
            for feature in self.utterance_features[utt_id]:
                self.feat_counts[feature] = \
                    self.feat_counts.get(feature, 0) + 1

        if verbose:
            print "Number of features: ", len(self.feat_counts)

        # Collect those with too few occurrences.
        low_count_features = set(filter(
            lambda feature: self.feat_counts[feature] < min_feature_count,
            self.feat_counts.keys()))

        # Discard the low-count features.
        for utt_id in self.utterances.keys():
            self.utterance_features[utt_id].prune(low_count_features)
        old_feat_counts = self.feat_counts
        self.feat_counts = {key: old_feat_counts[key]
                            for key in old_feat_counts
                            if key not in low_count_features}

        if verbose:
            print ("Number of features occurring less then {occs} times: {cnt}"
                   .format(occs=min_feature_count,
                           cnt=len(low_count_features)))

        # Build the mapping from features to their indices.
        self.feature_idxs = {}
        for idx, feature in enumerate(self.feat_counts.keys()):
            self.feature_idxs[feature] = idx

        if verbose:
            print "Number of features after pruning: ", len(self.feat_counts)

    @property
    def dai_counts(self):
        """a mapping { str(DAI) : number of occurrences in training DAs }"""
        # If `_dai_counts' have not been evaluated yet,
        if self._dai_counts is None:
            # Count occurrences of all DAIs in the DAs bound to this learner.
            _dai_counts = self._dai_counts = dict()
            for utt_id in self.utterances.keys():
                for dai in self.das[utt_id].dais:
                    dai_str = str(dai)
                    _dai_counts[dai_str] = _dai_counts.get(dai_str, 0) + 1
        return self._dai_counts

    def print_dai_counts(self):
        """Prints what `extract_classifiers(verbose=True)' would output in
        earlier versions.

        """
        for utt_id in self.utterances.keys():
            for dai in self.das[utt_id].dais:
                if dai.value and '-' not in dai.value:
                    print '#' * 120
                    print self.das[utt_id]
                    print self.utterances[utt_id]
                    print self.category_labels[utt_id]

    def prune_classifiers(self, min_dai_count=5, accept_dai=None):
        """Prunes classifiers for DAIs that cannot be reliably classified with
        these training data.

        Arguments:
            min_dai_count: minimum number of occurrences of a DAI for it
                to have its own classifier (this affects only non-atomic DAIs
                without abstracted category labels)
            accept_dai: custom fuction that takes a string representation of
                a DAI and returns True if that DAI should have its classifier,
                else False;

                The function gets called with the following tuple
                of arguments: (self, dai_str), where `self' is this
                DAILogRegClassifierLearning object, and `dai_str' the string
                representation of the DAI in question

        """
        # Define pruning criteria.
        if accept_dai is not None:
            _accept_dai = lambda dai_str: accept_dai(self, dai_str)
        else:
            def _accept_dai(dai_str):
                # Discard a DAI that has too few occurrences.
                # FIXME? What is the zero for? Is that a way to check whether that
                # DAI has any category labels in it?!
                cond1 = ('=' in dai_str
                        and '0' not in dai_str
                        and self._dai_counts[dai_str] < min_dai_count)
                # Discard a DAI in the form '(slotname="dontcare")'.
                cond2 = ('="dontcare"' in dai_str and '(="dontcare")' not in dai_str)
                # Discard a 'null()'. This classifier can be ignored since the null
                # dialogue act is a complement to all other dialogue acts.
                cond3 = 'null()' in dai_str

                # None of the conditions must hold.
                return not (cond1 | cond2 | cond3)

        # Do the pruning.
        old_dai_counts = self.dai_counts  # NOTE side effect from the getter
        self._dai_counts = {dai_str: old_dai_counts[dai_str]
                            for dai_str in old_dai_counts
                            if _accept_dai(dai_str)}

    def print_classifiers(self):
        print "Classifiers detected in the training data"
        print "-" * 120
        print "Number of classifiers: ", len(self._dai_counts)
        print "-" * 120

        for dai in sorted(self._dai_counts.keys()):
            print('%40s = %d' % (dai, self._dai_counts[dai]))

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
        parsed_dais = {dai: DialogueActItem(dai=dai) for dai in
                       self._dai_counts}
        das = self.das
        uts = self.utterances.keys()
        # NOTE that the output matrix has unusual indexing: first associative
        # index to columns, then integral index to rows.
        self._output_matrix = \
            {dai: np.array([float(parsed_dais[dai] in das[utt_id])
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
        self._input_matrix = np.zeros((len(self.utterances),
                                       len(self.feat_counts)))
        for utt_idx, utt_id in enumerate(self.utterances.keys()):
            self._input_matrix[utt_idx] = (
                self.utterance_features[utt_id]
                .get_feature_vector(self.feature_idxs))

    def train(self, sparsification=1.0, verbose=True):
        # Make sure the input and output matrices has been generated.
        if self._output_matrix is None:
            self.gen_output_matrix()
        if self._input_matrix is None:
            self.gen_input_matrix()

        self.trained_classifiers = {}
        if verbose:
            coefs_sum = np.zeros(shape=(1, len(self.feat_counts)))
        for dai in sorted(self._dai_counts):
            # before message
            if verbose:
                print "Training classifier: ", dai

            # Train and store the classifier for `dai'.
            lr = LogisticRegression('l1', C=sparsification, tol=1e-6)
            lr.fit(self._input_matrix, self._output_matrix[dai])
            self.trained_classifiers[dai] = lr

            # after message
            if verbose:
                coefs_sum += lr.coef_
                mean_accuracy = lr.score(self._input_matrix,
                                         self._output_matrix[dai])
                msg = ("Mean accuracy for training data: {acc:6.2f} %\n"
                       "Size of the params: {parsize}\n"
                       "Number of non-zero params: {nonzero}\n").format(
                       acc=(100.0 * mean_accuracy),
                       parsize=lr.coef_.shape,
                       nonzero=np.count_nonzero(lr.coef_))
                # The claim about number of non-zero coefficients is correct
                # with probability close to 1, and that's good enough.  I mean,
                # a set of non-zero coefficients may sum up to zero.
                print msg

        if verbose:
            print "Total number of non-zero params:", \
                  np.count_nonzero(coefs_sum)

    def save_model(self, file_name):
        data = (self.feat_counts.keys(),
                self.feature_idxs,
                self.trained_classifiers,
                self.features_type,
                self.features_size)
        with open(file_name, 'w+') as outfile:
            pickle.dump(data, outfile)


class DAILogRegClassifier(SLUInterface):
    """This class implements a parser based on set of classifiers for each
    dialogue act item. When parsing the input utterance, the parse classifies
    whether a given dialogue act item is present. Then, the output dialogue
    act is composed of all detected dialogue act items.

    Dialogue act is defined as a composition of dialogue act items. E.g.

    confirm(drinks="wine")&inform(name="kings shilling") <=> 'does kings serve wine'

    where confirm(drinks="wine") and inform(name="kings shilling") are two
    dialogue act items.

    This parser uses logistic regression as the classifier of the dialogue
    act items.

    """
    def __init__(self, preprocessing=None):
        # FIXME: maybe the SLU components should use the Config class to
        # initialise themselves.  As a result it would create their category
        # label database and pre-processing classes.

        self.preprocessing = preprocessing

    def load_model(self, file_name):
        with open(file_name, 'r') as infile:
            data = pickle.load(infile)
        self.features_list, self.feature_idxs, self.trained_classifiers, \
            self.features_type, self.features_size = data

    def get_size(self):
        return len(self.features_list)

    def parse_1_best(self, utterance, verbose=False):
        """Parse `utterance' and generate the best interpretation in the form
        of a dialogue act (an instance of DialogueAct).

        The result is the dialogue act confusion network.

        """
        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        if verbose:
            print utterance

        if self.preprocessing:
            utterance = self.preprocessing.text_normalisation(utterance)
            utterance, category_labels = \
                self.preprocessing.values2category_labels_in_utterance(
                    utterance)

        if verbose:
            print utterance
            print category_labels

        # Generate utterance features.
        utterance_features = UtteranceFeatures(self.features_type,
                                               self.features_size,
                                               utterance)

        if verbose:
            print utterance_features

        kernel_vector = np.zeros((1, len(self.feature_idxs)))
        kernel_vector[0] = utterance_features.get_feature_vector(
            self.feature_idxs)

        da_confnet = DialogueActConfusionNetwork()
        for dai in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", dai

            p = self.trained_classifiers[dai].predict_proba(kernel_vector)

            if verbose:
                print p

            da_confnet.add(p[0][1], DialogueActItem(dai=dai))

        if verbose:
            print "DA: ", da_confnet

        confnet = self.preprocessing.category_labels2values_in_confnet(
            da_confnet, category_labels)
        confnet.sort()

        return confnet

    def parse_nblist(self, utterance_list):
        """Parse N-best list by parsing each item in the list and then by
        merging the results."""

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
