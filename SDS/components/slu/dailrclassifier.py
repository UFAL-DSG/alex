#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import cPickle as pickle

from math import exp
from collections import defaultdict
from sklearn.linear_model import LogisticRegression

from SDS.components.asr.utterance import UtteranceFeatures
from da import DialogueActItem, DialogueAct


class DAILogRegClassifierLearning:
    """ Implements learning of dialogue act item classifiers based on logistic regression.
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

        # substitute category labels
        self.category_labels = {}
        if self.preprocessing:
            for k in self.utterances_list:
                self.utterances[k], self.das[k], self.category_labels[k] = self.preprocessing.values2category_labels_in_da(self.utterances[k], self.das[k])

        # generate utterance features
        self.utterance_features = {}
        for k in self.utterances_list:
            self.utterance_features[k] = UtteranceFeatures(
                self.features_type, self.features_size, self.utterances[k])

    def prune_features(self, min_feature_count=5, verbose=False):
        """Prune those features that are unique. They are irrelevant for computing dot kernels.
        """
        # collect all features and prune those occurring only once
        features = defaultdict(int)
        for u in self.utterances_list:
            for f in self.utterance_features[u]:
                features[f] += 1

        if verbose:
            print "Number of features: ", len(features)

        self.remove_features = []
        i = 0
        for k in features:
            if features[k] < min_feature_count:
                self.remove_features.append(k)

        if verbose:
            print "Number of features occurring less then %d times: %d" % (
                min_feature_count, len(self.remove_features))

        self.remove_features = set(self.remove_features)
        for u in self.utterances_list:
            self.utterance_features[u].prune(self.remove_features)

        self.features = defaultdict(int)
        for u in self.utterances_list:
            for f in self.utterance_features[u]:
                self.features[f] += 1

        self.features_list = self.features.keys()

        self.features_mapping = {}
        for i, f in enumerate(self.features_list):
            self.features_mapping[f] = i

        if verbose:
            print "Number of features after pruning: ", len(self.features)

    def extract_classifiers(self, verbose=False):
        # get the classifiers
        self.classifiers = defaultdict(int)

        for k in self.utterances_list:
            for dai in self.das[k].dais:
                self.classifiers[str(dai)] += 1

                if verbose:
                    if dai.value and '-' not in dai.value:
                        print '#' * 120
                        print self.das[k]
                        print self.utterances[k]
                        print self.category_labels[k]

    def prune_classifiers(self, min_classifier_count=5):
        new_classifiers = {}
        for k in self.classifiers:
            if '=' in k and '0' not in k and self.classifiers[k] < min_classifier_count:
                continue

            if '="dontcare"' in k and '(="dontcare")' not in k:
                continue

            new_classifiers[k] = self.classifiers[k]

        self.classifiers = new_classifiers

    def gen_data_for_classifiers(self):
        # generate training data
        self.classifiers_training_data = defaultdict(list)

        parsed_classfiers = {}
        for c in self.classifiers:
            parsed_classfiers[c] = DialogueActItem()
            parsed_classfiers[c].parse(c)

        for u in self.utterances_list:
            for c in self.classifiers:
                if parsed_classfiers[c] in self.das[u]:
                    self.classifiers_training_data[c].append(1.0)
                else:
                    self.classifiers_training_data[c].append(0.0)

        for c in self.classifiers:
            self.classifiers_training_data[c] = np.array(
                self.classifiers_training_data[c])

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
                u].get_feature_vector(self.features_mapping)

    def train(self, sparsification=1.0, verbose=True):
        self.trained_classifiers = {}

        non_zero = np.zeros(shape=(1, len(self.features_list)))

        for c in sorted(self.classifiers):
            if verbose:
                print "Training classifier: ", c

            lr = LogisticRegression('l1', C=sparsification, tol=1e-6)
            lr.fit(self.kernel_matrix, self.classifiers_training_data[c])
            self.trained_classifiers[c] = lr

            non_zero += lr.coef_

            if verbose:
                mean_accuracy = lr.score(
                    self.kernel_matrix, self.classifiers_training_data[c])
                print "Training data prediction mean accuracy of the training data: %6.2f" % (100.0 * mean_accuracy, )
                print "Size of the params:", lr.coef_.shape, "Number of non-zero params:", np.count_nonzero(lr.coef_)

        if verbose:
            print "Total number of non-zero params:", np.count_nonzero(
                non_zero)

    def save_model(self, file_name):
        f = open(file_name, 'w+')
        d = [self.features_list,
             self.features_mapping,
             self.trained_classifiers,
             self.features_type,
             self.features_size]

        pickle.dump(d, f)
        f.close()


class DAILogRegClassifier:
    """
      This parser implements a parser based on set of classifiers for each dialogue act item. When parsing
      the input utterance, the parse classifies whether a given dialogue act item is present. Then, the output
      dialogue act is composed of all detected dialogue act items.

      Dialogue act is defined as a composition of dialogue act items. E.g.

        confirm(drinks="wine")&inform(name="kings shilling") <=> 'does kings serve wine'

      where confirm(drinks="wine") and inform(name="kings shilling") are two dialogue act items.

      This parser uses logistic regression as the classifier of the dialogue act items.

    """
    def __init__(self, preprocessing=None):
        self.preprocessing = preprocessing

    def load_model(self, file_name):
        f = open(file_name, 'r')
        d = pickle.load(f)
        self.features_list, self.features_mapping, self.trained_classifiers, self.features_type, self.features_size = d
        f.close()

    def get_size(self):
        return len(self.features_list)

    def parse(self, utterance, verbose=False):
        """Parse utterance and generate the best interpretation in the form of an dialogue act (an instance
        of DialogueAct.
        """

        if verbose:
            print utterance

        if self.preprocessing:
            utterance, category_labels = self.preprocessing.values2category_labels_in_utterance(utterance)

        if verbose:
            print utterance
            print category_labels

        # generate utterance features
        utterance_features = UtteranceFeatures(
            self.features_type, self.features_size, utterance)

        if verbose:
            print utterance_features

        kernel_vector = np.zeros((1, len(self.features_mapping)))
        kernel_vector[0] = utterance_features.get_feature_vector(
            self.features_mapping)

        da = []
        prob = 1.0

        for c in self.trained_classifiers:
            if verbose:
                print "Classifying classifier: ", c

            p = self.trained_classifiers[c].predict_proba(kernel_vector)

            if verbose:
                print p

            if p[0][0] < 0.5:
                da.append(c)
                prob *= p[0][1]
                    # multiply with probability of presence of a dialogue act
            else:
                prob *= p[0][0]  # multiply with probability of exclusion  of a dialogue act

        if not da:
            da.append('null()')

        da = '&'.join(da)

        if verbose:
            print "DA: ", da

        da = DialogueAct(da)
        da = self.preprocessing.category_labels2values_in_da(
            da, category_labels)

        return da, prob

    def parse_N_best_list(self, hyp_list):
        sluHyp = []
        #sluHyp = ["dialogue act", 0.X]*N

        #TODO: implement

        for h in hyp_list:
            pass

        return sluHyp

    def parse_confusion_network(self, conf_net):
        utterance = utterance.conf_net.best_hyp()

        #TODO: implement

        if verbose:
            print utterance

        if self.preprocessing:
            utterance, category_labels = self.preprocessing.values2category_labels_in_utterance(utterance)

        if verbose:
            print utterance
            print category_labels

        # generate utterance features
        utterance_features = UtteranceFeatures(
            self.features_type, self.features_size, utterance)

        if verbose:
            print utterance_features

        kernel_vector = np.zeros((1, len(self.features_mapping)))
        kernel_vector[0] = utterance_features.get_feature_vector(
            self.features_mapping)

        dacn = {}
        for c in self.trained_classifiers:
            if verbose:
                print "Classifying classifier: ", c

            p = self.trained_classifiers[c].predict_proba(kernel_vector)

            if verbose:
                print p

            if p[0][0] < 0.5:
                da.append(c)

            dacn[c] = (p[0][1], p[0][0])

        dacn = DialogueActConfusionNetwork(dacn)
        dacn = self.preprocessing.category_labels2values_in_da(
            dacn, category_labels)

        return dacn
