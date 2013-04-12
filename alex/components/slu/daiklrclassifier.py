#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict
import cPickle as pickle
from math import exp
import numpy as np

from sklearn.linear_model import LogisticRegression

from exception import SLUException
from da import DialogueActItem, DialogueAct
from dailrclassifier import *


class DAIKernelException(SLUException):
    pass


class DAIDotKernel(object):
    """Compute dot kernel function for specific feature vectors.
    """
    def __init__(self):
        pass

    def __call__(self, f1, f2):
        """Compute dot product kernel function.
        """

        r = 0.0
        for f in f1:
            if f in f2:
                r += f1[f] * f2[f]

        return r


class DAIAprxDotKernel(object):
    """Compute approximate dot kernel function for specific feature vectors.
    """
    def __init__(self):
        pass

    def __call__(self, f1, f2):
        """Compute dot product kernel function.
        """
        # return len(f1.set & f2.set)
        return len(set(f1.features) & set(f2.features))


class DAIRadialKernel(object):
    """Compute radial kernel function for specific feature vectors.
    """
    def __init__(self, gamma=1.0):
        self.gamma = gamma

    def __call__(self, f1, f2):
        """Compute the radial basis kernel function.
        """
        sq_norm = 0.0

        for f in f1:
            if f in f2:
                sq_norm += (f1[f] - f2[f]) ** 2
            else:
                sq_norm += (f1[f]) ** 2
        for f in f2:
            if f not in f1:
                sq_norm += (f2[f]) ** 2

        return exp(-self.gamma * sq_norm)


class DAIAprxRadialKernel(object):
    """Compute approximate radial kernel function for specific feature vectors.
    """
    def __init__(self, gamma=1.0):
        self.gamma = gamma

    def __call__(self, f1, f2):
        """Compute the radial basis kernel function.
        """
        r = len(set(f1.features) ^ set(f2.features))

        return exp(-self.gamma * r)


class DAIKerLogRegClassifierLearning(object):
    """Implements learning of dialogue act item classifiers based on kernelized
    logistic regression.
    """

    def __init__(self,
                 preprocessing=None,
                 kernel_type='adot',
                 kernel_gamma=0.05,
                 features_type='ngram',
                 features_size=3):
        self.kernel_type = kernel_type
        self.kernel_gamma = kernel_gamma
        self.features_type = features_type
        self.features_size = features_size

        self.preprocessing = preprocessing

        if self.kernel_type == 'adot':
            self.kernel = DAIAprxDotKernel()
        elif self.kernel_type == 'dot':
            self.kernel = DAIDotKernel()
        elif self.kernel_type == 'aradial':
            self.kernel = DAIAprxRadialKernel(kernel_gamma)
        elif self.kernel_type == 'radial':
            self.kernel = DAIRadialKernel(kernel_gamma)

    def process_data(self, utterances, das, verbose=False):
        self.utterances = utterances
        self.das = das

        # substitute category labels
        self.category_labels = {}
        if self.preprocessing:
            for k in self.utterances:
                self.utterances[k] = self.preprocessing.text_normalisation(
                    self.utterances[k])
                (self.utterances[k], self.das[k], self.category_labels[k]) = (
                    self.preprocessing.values2category_labels_in_da(
                        self.utterances[k], self.das[k]))

        # generate utterance features
        self.utterance_features = {}
        for k in self.utterances:
            self.utterance_features[k] = UtteranceFeatures(
                self.features_type, self.features_size, self.utterances[k])

        self.utterance_features_list = self.utterance_features.keys()

    def extract_classifiers(self, prune=10, verbose=False):
        # get the classifiers
        self.classifiers = defaultdict(int)

        for k in self.utterance_features_list:
            for dai in self.das[k].dais:
                self.classifiers[str(dai)] += 1

                if verbose:
                    if dai.value and '-' not in dai.value:
                        print '#' * 120
                        print self.das[k]
                        print self.utterances[k]
                        print self.category_labels[k]

        new_classifiers = {}
        for k in self.classifiers:
            if '=' in k and '0' not in k and self.classifiers[k] < 5:
                continue

            if '="dontcare"' in k and '(="dontcare")' not in k:
                continue

            new_classifiers[k] = self.classifiers[k]

        self.classifiers = new_classifiers

        # generate training data
        self.classifiers_training_data = defaultdict(list)

        parsed_classfiers = {}
        for c in self.classifiers:
            parsed_classfiers[c] = DialogueActItem()
            parsed_classfiers[c].parse(c)
        for k in self.utterance_features_list:
            for c in self.classifiers:
                if parsed_classfiers[c] in self.das[k]:
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

    def prune_features(self, verbose=False):
        """Prune those features that are unique. They are irrelevant for
        computing dot kernels.
        """
        # Collect all features and prune those occurring only once.
        features = defaultdict(int)
        for k in self.utterance_features:
            for f in self.utterance_features[k]:
                features[f] += 1

        if verbose:
            print "Total number of features: ", len(features)

        self.remove_features = []
        for k in features:
            if features[k] <= 2:
                self.remove_features.append(k)

        if verbose:
            print "Number of unique features: ", len(self.remove_features)

        self.remove_features = set(self.remove_features)
        for k in self.utterance_features:
            self.utterance_features[k].prune(self.remove_features)

        features = defaultdict(int)
        for k in self.utterance_features:
            for f in self.utterance_features[k]:
                features[f] += 1

        if verbose:
            print "Total number of features: ", len(features)

    def compute_kernel_matrix(self, verbose=False):
        self.kernel_matrix = np.zeros((len(self.utterance_features_list),
                                       len(self.utterance_features_list)))

        every_n_feature = int(len(self.utterance_features_list) / 100)
        for i, f1 in enumerate(self.utterance_features_list):
            if verbose and (i % every_n_feature == 0):
                print "Computing: %s row, Processed %6.1f%%" % (
                    f1, 100.0 * i / len(self.utterance_features_list))

            for j, f2 in enumerate(self.utterance_features_list):
                self.kernel_matrix[i][j] = self.kernel(
                    self.utterance_features[f1], self.utterance_features[f2])

    def train(self, sparsification=0.5, verbose=True):
        self.trained_classifiers = {}

        non_zero = np.zeros(shape=(1, len(self.utterance_features_list)))

        for c in sorted(self.classifiers):
            if verbose:
                print "Training classifier: ", c

            lr = LogisticRegression('l2', C=sparsification, tol=1e-6)
            lr.fit(self.kernel_matrix, self.classifiers_training_data[c])
            self.trained_classifiers[c] = lr

            non_zero += lr.coef_

            if verbose:
                mean_accuracy = lr.score(
                    self.kernel_matrix, self.classifiers_training_data[c])
                print ("Training data prediction mean accuracy of the "
                       "training data: {0:6.2f}").format(100.0 * mean_accuracy)
                print "Size of the params:", lr.coef_.shape, ("Number of "
                      "non-zero params:"), np.count_nonzero(lr.coef_)

        if verbose:
            print "Total number of non-zero params:", np.count_nonzero(
                non_zero)

        # perform sparsification

    def get_trained_classfiers(self):
        return self.trained_classifiers

    def save_model(self, file_name):
        f = open(file_name, 'w+')
        d = [self.kernel,
             self.trained_classifiers,
             self.utterance_features_list,
             self.utterance_features]

        pickle.dump(d, f)
        f.close()


class DAIKerLogRegClassifier(object):
    """
      This parser implements a parser based on set of classifiers for each
      dialogue act item. When parsing the input utterance, the parse classifies
      whether a given dialogue act item is present. Then, the output dialogue
      act is composed of all detected dialogue act items.

      Dialogue act is defined as a composition of dialogue act items. E.g.

        confirm(drinks="wine")&inform(name="kings shilling")
            <=>
        'does kings serve wine'

      where confirm(drinks="wine") and inform(name="kings shilling") are two
      dialogue act items.

      This parser uses kernelized logistic regression as the classifier of the
      dialogue act items.

    """
    def __init__(self,
                 preprocessing=None,
                 features_type='ngram',
                 features_size=3):
        self.features_type = features_type
        self.features_size = features_size

        self.preprocessing = preprocessing

    def load_model(self, file_name):
        with open(file_name, 'rb') as infile:
            data = pickle.load(infile)
        (self.kernel, self.trained_classifiers, self.utterance_features_list,
         self.utterance_features) = data

    def get_size(self):
        return len(self.utterance_features_list)

    def parse(self, utterance, verbose=False):
        """Parse utterance and generate the best interpretation in the form of
        an dialogue act (an instance of DialogueAct.
        """
        if verbose:
            print utterance

        if self.preprocessing:
            utterance = self.preprocessing.text_normalisation(utterance)
            utterance, category_labels = (
                self.preprocessing.values2category_labels_in_utterance(
                    utterance))

        if verbose:
            print utterance
            print category_labels

        # generate utterance features
        utterance_features = UtteranceFeatures(
            self.features_type, self.features_size, utterance)

        if verbose:
            print utterance_features

        kernel_vector = np.zeros((1, len(self.utterance_features_list)))
        for j, f in enumerate(self.utterance_features_list):
            kernel_vector[0][j] = self.kernel(
                utterance_features, self.utterance_features[f])

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
                prob *= p[0][0]  # multiply with probability of absence of
                                 # a dialogue act

        if not da:
            da.append('null()')

        da = '&'.join(da)

        if verbose:
            print "DA: ", da

        da = DialogueAct(da)
        da = self.preprocessing.category_labels2values_in_da(
            da, category_labels)

        return prob, da
