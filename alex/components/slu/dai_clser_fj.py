#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.
"""
The original FJ's implementation of the DAI classifier.
"""

import numpy as np
import cPickle as pickle

from collections import defaultdict
from sklearn.linear_model import LogisticRegression

from alex.components.asr.utterance import UtteranceFeatures, UtteranceHyp
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork, merge_slu_confnets


class DAILogRegClassifier(SLUInterface):
    """Implements learning of dialogue act item classifiers based on logistic
    regression.

    The parser implements a parser based on set of classifiers for each
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

    def __init__(self,
                 preprocessing=None,
                 features_size=4,
                 *args, **kwargs):
        self.features_size = features_size
        self.preprocessing = preprocessing

        # Bookkeeping.
        self._dai_counts = None
        self._input_matrix = None
        self._outputs = None

    def extract_features(self, obss, das, verbose=False):
        self.utterances = obss['utt']
        self.das = das

        self.utterances_list = self.utterances.keys()

        # substitute category labels
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
                UtteranceFeatures('ngram',
                                  self.features_size,
                                  self.utterances[utt_idx])

    def prune_features(self, min_feature_count=5, verbose=False,
                       *args, **kwargs):
        """Prune those features that are unique. They are irrelevant for
        computing dot kernels.
        """
        # Collect all features and prune those occurring only once.
        features = defaultdict(int)
        for utt in self.utterances_list:
            for feat in self.utterance_features[utt]:
                features[feat] += 1

        if verbose:
            print "Number of features: ", len(features)

        self.remove_features = []
        for feat in features:
            if features[feat] < min_feature_count:
                self.remove_features.append(feat)

        if verbose:
            print "Number of features occurring less then %d times: %d" % (
                min_feature_count, len(self.remove_features))

        self.remove_features = set(self.remove_features)
        for utt in self.utterances_list:
            self.utterance_features[utt].prune(self.remove_features)

        self.features = defaultdict(int)
        for utt in self.utterances_list:
            for feat in self.utterance_features[utt]:
                self.features[feat] += 1

        self.features_list = self.features.keys()

        self.features_mapping = {}
        for feat_idx, feat in enumerate(self.features_list):
            self.features_mapping[feat] = feat_idx

        if verbose:
            print "Number of features after pruning: ", len(self.features)

    @property
    def dai_counts(self):
        # If a cached result is not available,
        if self._dai_counts is None:
            # count the dais and store the result.
            self._dai_counts = defaultdict(int)
            for utt_idx in self.utterances_list:
                for dai in self.das[utt_idx].dais:
                    self._dai_counts[dai] += 1

                    # if verbose:
                        # if dai.value and '-' not in dai.value:
                            # print '#' * 120
                            # print self.das[utt_idx]
                            # print self.utterances[utt_idx]
                            # print self.category_labels[utt_idx]
        return self._dai_counts

    def prune_classifiers(self, min_dai_count=5, *args, **kwargs):
        new_classifiers = {}
        for dai in self.dai_counts:
            dai_str = str(dai)
            # Prune these classfiers.
            if ('=' in dai_str
                    and '0' not in dai_str
                    and self.dai_counts[dai] < min_dai_count):
                continue

            if ('="dontcare"' in dai_str
                    and '(="dontcare")' not in dai_str):
                continue

            if 'null()' in dai_str:
                # null() classifier is not necessary since null dialogue act is
                # a complement to all other dialogue acts.
                continue

            new_classifiers[dai] = self.dai_counts[dai]

        self._dai_counts = new_classifiers

    def gen_outputs(self):
        # Generate training data.
        self._outputs = defaultdict(list)

        for utt in self.utterances_list:
            for dai in self.dai_counts:
                if dai in self.das[utt]:
                    self._outputs[dai].append(1.0)
                else:
                    self._outputs[dai].append(0.0)

        for dai in self.dai_counts:
            self._outputs[dai] = np.array(self._outputs[dai])

    @property
    def outputs(self):
        if self._outputs is None:
            self.gen_outputs()
        return self._outputs

    def print_classifiers(self):
        print "Classifiers detected in the training data"
        print "-" * 120
        print "Number of classifiers: ", len(self.dai_counts)
        print "-" * 120

        for dai in sorted(self.dai_counts):
            print('%40s = %d' % (dai, self.dai_counts[dai]))

    def gen_input_matrix(self, verbose=False):
        self._input_matrix = np.zeros(
            (len(self.utterances_list), len(self.features_list)))

        every_n_feature = int(len(self.utterances_list) / 10)
        for utt_idx, utt in enumerate(self.utterances_list):
            if verbose and (utt_idx % every_n_feature == 0):
                print "Computing features for %s, processed %6.1f%%" % (
                    utt, 100.0 * utt_idx / len(self.utterances_list))

            self._input_matrix[utt_idx] = self.utterance_features[
                utt].get_feature_vector(self.features_mapping)

    @property
    def input_matrix(self):
        if self._input_matrix is None:
            self.gen_input_matrix(verbose=False)
        return self._input_matrix

    def train(self, sparsification=1.0, verbose=True, *args, **kwargs):
        self.trained_classifiers = {}

        non_zero = np.zeros(shape=(1, len(self.features_list)))

        for dai in sorted(self.dai_counts):
            if verbose:
                print "Training classifier: ", dai

            lr = LogisticRegression('l1', C=sparsification, tol=1e-6)
            lr.fit(self.input_matrix, self.outputs[dai])
            self.trained_classifiers[dai] = lr

            non_zero += lr.coef_

            if verbose:
                mean_accuracy = lr.score(
                    self.input_matrix, self.outputs[dai])
                print (u"Training data prediction mean accuracy of the "
                       u"training data: {0:6.2f}").format(100.0 * mean_accuracy)
                print "Size of the params:", lr.coef_.shape, \
                      "Number of non-zero params:", np.count_nonzero(lr.coef_)

        if verbose:
            print "Total number of non-zero params:", np.count_nonzero(
                non_zero)

    def save_model(self, file_name, gzip=None):
        data = [self.features_list, self.features_mapping,
                self.trained_classifiers, self.features_size]

        if gzip is None:
            gzip = file_name.endswith('gz')
        if gzip:
            import gzip
            open_meth = gzip.open
        else:
            open_meth = open
        with open_meth(file_name, 'wb') as outfile:
            pickle.dump(data, outfile)

    def load_model(self, file_name):
        # Handle gzipped files.
        if file_name.endswith('gz'):
            import gzip
            open_meth = gzip.open
        else:
            open_meth = open

        with open_meth(file_name, 'rb') as model_file:
            (self.features_list, self.features_mapping,
             self.trained_classifiers,
             self.features_size) = pickle.load(model_file)

    def get_size(self):
        return len(self.features_list)

    def parse_1_best(self, obs=dict(), ret_cl_map=False, verbose=False,
                     *args, **kwargs):
        """
        Parse `utterance' and generate the best interpretation in the form of
        a dialogue act (an instance of DialogueAct).

        The result is the dialogue act confusion network.

        """
        utterance = obs.get('utt', None)
        if utterance is None:
            from exception import DAILRException
            raise DAILRException("Need to get an utterance to parse.")
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
        utterance_features = UtteranceFeatures('ngram',
                                               self.features_size,
                                               utterance)

        if verbose:
            print utterance_features

        kernel_vector = np.zeros((1, len(self.features_mapping)))
        kernel_vector[0] = utterance_features.get_feature_vector(
            self.features_mapping)

        da_confnet = DialogueActConfusionNetwork()
        for dai in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", str(dai)

            p = self.trained_classifiers[dai].predict_proba(kernel_vector)

            if verbose:
                print p

            da_confnet.add(p[0][1], dai)

        if verbose:
            print "DA: ", da_confnet

        da_confnet = self.preprocessing.category_labels2values_in_confnet(
            da_confnet, category_labels)
        da_confnet.sort().merge()

        if ret_cl_map:
            return da_confnet, category_labels
        return da_confnet


    def parse_nblist(self, obs, *args, **kwargs):
        """
        Parses n-best list by parsing each item on the list and then merging
        the results.
        """

        utterance_list = obs['utt_nbl']
        if len(utterance_list) == 0:
            from exception import DAILRException
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

    def parse_confnet(self, obs, verbose=False, *args, **kwargs):
        """
        Parses the word confusion network by generating an n-best list and
        parsing this n-best list.
        """
        confnet = obs['utt_cn']
        nblist = confnet.get_utterance_nblist(n=40)
        sem = self.parse_nblist(nblist)
        return sem
