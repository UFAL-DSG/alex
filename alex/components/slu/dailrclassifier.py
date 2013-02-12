#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

import numpy as np
import cPickle as pickle

from collections import defaultdict
from sklearn.linear_model import LogisticRegression

from alex.components.asr.utterance import UtteranceFeatures, UtteranceHyp
from alex.components.slu.__init__ import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork, merge_slu_confnets
from alex.utils.exception import DAILRException


class DAILogRegClassifierLearning(object):
    """Implements learning of dialogue act item classifiers based on logistic
    regression.

    """

    def __init__(self,
                 preprocessing=None,
                 features_type='ngram',
                 features_size=4):
        self.features_type = features_type
        self.features_size = features_size

        self.preprocessing = preprocessing

    def extract_features(self, utterances, das, verbose=False):
        self.utterances = utterances
        self.das = das

        self.utterances_list = self.utterances.keys()

        # Substitute category labels.
        self.category_labels = {}
        if self.preprocessing:
            for utt_idx in self.utterances_list:
                self.utterances[utt_idx] = self.preprocessing\
                    .text_normalisation(self.utterances[utt_idx])
                self.utterances[utt_idx], self.das[utt_idx], \
                        self.category_labels[utt_idx] = \
                    self.preprocessing.values2category_labels_in_da(
                        self.utterances[utt_idx], self.das[utt_idx])

        # Generate utterance features.
        self.utterance_features = {}
        for utt_idx in self.utterances_list:
            self.utterance_features[utt_idx] = \
                UtteranceFeatures(self.features_type,
                                  self.features_size,
                                  self.utterances[utt_idx])

    def prune_features(self, min_feature_count=5, verbose=False):
        """Prunes features that occur few times.

        Arguments:
            min_feature_count: minimum number of a feature occurring for it not
                               to be pruned (default: 5)
            verbose: whether to print diagnostic messages to
                               stdout (default: False)

        """
        # Count number of occurrences of features.
        self.feat_count = defaultdict(int)
        for utt_key in self.utterances_list:
            for feature in self.utterance_features[utt_key]:
                self.feat_count[feature] += 1

        if verbose:
            print "Number of features: ", len(self.feat_count)

        # Collect those with too few occurrences.
        low_count_features = set(filter(
            lambda feature: self.feat_count[feature] < min_feature_count,
            self.feat_count.keys()))

        # Discard the low-count features.
        for utt_key in self.utterances_list:
            self.utterance_features[utt_key].prune(low_count_features)
        for feature in low_count_features:
            del self.feat_count[feature]

        if verbose:
            print "Number of features occurring less then %d times: %d" % (
                min_feature_count, len(low_count_features))

        # Build auxiliary data structures listing the features, and mapping
        # them to their indices, respectively.
        self.features_list = self.feat_count.keys()
        self.feature_idxs = {}
        for idx, feature in enumerate(self.features_list):
            self.feature_idxs[feature] = idx

        if verbose:
            print "Number of features after pruning: ", len(self.feat_count)

    def extract_classifiers(self, verbose=False):
        # Get the classifiers.
        # XXX !? This does not get any classifiers. It merely counts DAI-s, and
        # saves these counts to the `self.classifiers' counter.
        self.classifiers = defaultdict(int)

        for utt_idx in self.utterances_list:
            for dai in self.das[utt_idx].dais:
                self.classifiers[str(dai)] += 1

                if verbose:
                    if dai.value and '-' not in dai.value:
                        print '#' * 120
                        print self.das[utt_idx]
                        print self.utterances[utt_idx]
                        print self.category_labels[utt_idx]

    def prune_classifiers(self, min_classifier_count=5):
        new_classifiers = {}
        for k in self.classifiers:
            # prune these classfiers
            if ('=' in k
                    and '0' not in k
                    and self.classifiers[k] < min_classifier_count):
                continue

            if ('="dontcare"' in k
                    and '(="dontcare")' not in k):
                continue

            if 'null()' in k:
                # null() classifier is not necessary since null dialogue act is
                # a complement to all other dialogue acts
                continue

            new_classifiers[k] = self.classifiers[k]

        self.classifiers = new_classifiers

    def gen_data_for_classifiers(self):
        # Generate training data.
        self.classifiers_training_data = defaultdict(list)

        parsed_clsers = {}
        for clser in self.classifiers:
            parsed_clsers[clser] = DialogueActItem()
            parsed_clsers[clser].parse(clser)

        for utt in self.utterances_list:
            for clser in self.classifiers:
                if parsed_clsers[clser] in self.das[utt]:
                    self.classifiers_training_data[clser].append(1.0)
                else:
                    self.classifiers_training_data[clser].append(0.0)

        for clser in self.classifiers:
            self.classifiers_training_data[clser] = np.array(
                self.classifiers_training_data[clser])

    def print_classifiers(self):
        print "Classifiers detected in the training data"
        print "-" * 120
        print "Number of classifiers: ", len(self.classifiers)
        print "-" * 120

        for k in sorted(self.classifiers):
            print('%40s = %d' % (k, self.classifiers[k]))

    def compute_kernel_matrix(self, verbose=False):
        self.kernel_matrix = np.zeros(
            (len(self.utterances_list), len(self.features_list)))

        every_n_feature = int(len(self.utterances_list) / 10)
        for i, u in enumerate(self.utterances_list):
            if verbose and (i % every_n_feature == 0):
                print "Computing features for %s, processed %6.1f%%" % (
                    u, 100.0 * i / len(self.utterances_list))

            self.kernel_matrix[i] = self.utterance_features[
                u].get_feature_vector(self.feature_idxs)

    def train(self, sparsification=1.0, verbose=True):
        self.trained_classifiers = {}

        non_zero = np.zeros(shape=(1, len(self.features_list)))

        for clser in sorted(self.classifiers):
            if verbose:
                print "Training classifier: ", clser

            lr = LogisticRegression('l1', C=sparsification, tol=1e-6)
            lr.fit(self.kernel_matrix, self.classifiers_training_data[clser])
            self.trained_classifiers[clser] = lr

            non_zero += lr.coef_
            # This is correct with probability close to 1, and that's good
            # enough.

            if verbose:
                mean_accuracy = lr.score(
                    self.kernel_matrix, self.classifiers_training_data[clser])
                print ("Training data prediction mean accuracy of the "
                       "training data: {0:6.2f}").format(100.0 * mean_accuracy)
                print "Size of the params:", lr.coef_.shape, \
                      "Number of non-zero params:", np.count_nonzero(lr.coef_)

        if verbose:
            print "Total number of non-zero params:", np.count_nonzero(
                non_zero)

    def save_model(self, file_name):
        f = open(file_name, 'w+')
        d = [self.features_list,
             self.feature_idxs,
             self.trained_classifiers,
             self.features_type,
             self.features_size]

        pickle.dump(d, f)
        f.close()


class DAILogRegClassifier(SLUInterface):
    """
      This parser implements a parser based on set of classifiers for each
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
        f = open(file_name, 'r')
        d = pickle.load(f)
        self.features_list, self.feature_idxs, self.trained_classifiers, \
            self.features_type, self.features_size = d
        f.close()

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
        for clser in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", clser

            p = self.trained_classifiers[clser].predict_proba(kernel_vector)

            if verbose:
                print p

            da_confnet.add(p[0][1], DialogueActItem(dai=clser))

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
