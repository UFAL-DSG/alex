#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.
#
# TODO:
#   Document the DAILogRegClassifier class.
#   Merge the two classes?


from math import isnan
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
        dai_counts: mapping { DAI: number of occurrences in data }
        das: mapping { utterance ID: DA } for DAs corresponding to training
             utterances
        feat_counts: mapping { feature: number of occurrences }
        feature_idxs: mapping { feature: feature index }; feature indices span
                      range(0, number_of_features)
        features_size: size (order) of features, i.e., length of the n-grams
        features_type: type of features (only 'ngram' is supported now)
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
        utterance_features: mapping { utterance ID: utterance features } where
                            the features is an UtteranceFeatures object
        utterances: mapping { utterance ID: utterance } for training utterances

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
            for utt_id in self.utterances.iterkeys():
                # Normalise the text.
                self.utterances[utt_id] = self.preprocessing\
                    .text_normalisation(self.utterances[utt_id])
                # Substitute category labes.
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
        for utt_id in self.utterances.iterkeys():
            for feature in self.utterance_features[utt_id]:
                self.feat_counts[feature] = \
                    self.feat_counts.get(feature, 0) + 1

        if verbose:
            print "Number of features: ", len(self.feat_counts)

        # Collect those with too few occurrences.
        low_count_features = set(filter(
            lambda feature: self.feat_counts[feature] < min_feature_count,
            self.feat_counts.iterkeys()))

        # Discard the low-count features.
        for utt_id in self.utterances.iterkeys():
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
        for idx, feature in enumerate(self.feat_counts.iterkeys()):
            self.feature_idxs[feature] = idx

        if verbose:
            print "Number of features after pruning: ", len(self.feat_counts)

    @property
    def dai_counts(self):
        """a mapping { DAI : number of occurrences in training DAs }"""
        # If `_dai_counts' have not been evaluated yet,
        if self._dai_counts is None:
            # Count occurrences of all DAIs in the DAs bound to this learner.
            _dai_counts = self._dai_counts = dict()
            for utt_id in self.utterances.iterkeys():
                for dai in self.das[utt_id].dais:
                    _dai_counts[dai] = _dai_counts.get(dai, 0) + 1
        return self._dai_counts

    def print_dais(self):
        """Prints what `extract_classifiers(verbose=True)' would output in
        earlier versions.

        """
        for utt_id in self.utterances.iterkeys():
            for dai in self.das[utt_id].dais:
                # XXX What again does ('-' not in dai.value) check? Presence of
                # a category label? This seems to be the case yet it is very
                # cryptic.
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
                of arguments: (self, dai), where `self' is this
                DAILogRegClassifierLearning object, and `dai' the DAI in
                question

        """
        # Define pruning criteria.
        if accept_dai is not None:
            _accept_dai = lambda dai: accept_dai(self, dai)
        else:
            def _accept_dai(dai):
                # Discard a DAI that is reasonably complex and yet has too few
                # occurrences.
                if (dai.name is not None
                        and dai.value is not None
                        and not dai.has_category_label()
                        and self._dai_counts[dai] < min_dai_count):
                    return False
                # Discard a DAI in the form '(slotname="dontcare")'.
                if dai.name is not None and dai.value == "dontcare":
                    return False
                # Discard a 'null()'. This classifier can be ignored since the null
                # dialogue act is a complement to all other dialogue acts.
                return not dai.is_null()

        # Do the pruning.
        old_dai_counts = self.dai_counts  # NOTE the side effect from the getter
        self._dai_counts = {dai: old_dai_counts[dai]
                            for dai in old_dai_counts
                            if _accept_dai(dai)}

    def print_classifiers(self):
        print "Classifiers detected in the training data"
        print "-" * 120
        print "Number of classifiers: ", len(self._dai_counts)
        print "-" * 120

        for dai in sorted(self._dai_counts.iterkeys()):
            print '{dai:>40} = {cnt}'.format(dai=dai,
                                             cnt=self._dai_counts[dai])

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
        uts = self.utterances.viewkeys()
        # NOTE that the output matrix has unusual indexing: first associative
        # index to columns, then integral index to rows.
        self._output_matrix = \
            {dai.extension(): np.array([float(dai in das[utt_id])
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
        for utt_idx, utt_id in enumerate(self.utterances.iterkeys()):
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

            # Select from the training data only those with non-NaN values.
            outputs = self._output_matrix[dai]
            valid_row_idxs = set(
                [row_idx for row_idx in xrange(len(self._input_matrix))
                 if not isnan(outputs[row_idx])])
            if len(valid_row_idxs) == len(outputs):
                inputs = self._input_matrix
            else:
                inputs = np.array(
                    [row for row_idx, row in enumerate(self._input_matrix)
                     if row_idx in valid_row_idxs])
                outputs = np.array(
                    [output for row_idx, output in enumerate(outputs)
                     if row_idx in valid_row_idxs])
            if verbose:
                print "Support for training: {sup} (pos: {pos}, neg: {neg})"\
                    .format(sup=len(valid_row_idxs),
                            pos=len(filter(lambda out: out == 1., outputs)),
                            neg=len(filter(lambda out: out == 0., outputs)))

            # Train and store the classifier for `dai'.
            lr = LogisticRegression('l1', C=sparsification, tol=1e-6)
            lr.fit(inputs, outputs)
            self.trained_classifiers[dai] = lr

            # after message
            if verbose:
                coefs_sum += lr.coef_
                mean_accuracy = lr.score(inputs, outputs)
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

    @classmethod
    def resave_model(self, infname, outfname):
        """This helper method serves to convert from the original format of SLU
        models to the current one.

        """
        with open(infname, 'rb') as infile:
            data = pickle.load(infile)
        new_clsers = {DialogueActItem(dai): clser for dai, clser in
                      data[2].iteritems()}

        #import ipdb; ipdb.set_trace()
        with open(outfname, 'wb+') as outfile:
            pickle.dump((data[0], data[1], new_clsers, data[3], data[4]),
                        outfile)

    def save_model(self, file_name):
        data = (self.feat_counts.keys(),
                self.feature_idxs,
                {dai.extension(): clser for dai, clser in
                 self.trained_classifiers.iteritems()},
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

            try:
                p = self.trained_classifiers[dai].predict_proba(kernel_vector)
            except Exception, e:
                print 'except', e
                continue

            if verbose:
                print p

            da_confnet.add(p[0][1], dai)

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
