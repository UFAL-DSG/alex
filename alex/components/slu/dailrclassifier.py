#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a rewrite of the DAILogRegClassifier ``from dailrclassifier_old.py``. The underlying approach is the same; however,
the way how the features are computed is changed significantly.
"""
from __future__ import unicode_literals

import copy
import numpy as np
import cPickle as pickle

from collections import defaultdict
from sklearn.linear_model import LogisticRegression
from scipy.sparse import lil_matrix

from alex.components.asr.utterance import Utterance, UtteranceHyp, UtteranceNBList, UtteranceConfusionNetwork
from alex.components.slu.exceptions import DAILRException
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork
from alex.utils.cache import lru_cache

CONFNET2NBLIST_EXPANSION_APPROX = 40


class Features(object):
    """
    This is a simple feature object. It is a light version of an unnecessary complicated alex.ml.features.Features class.
    """

    def __init__(self):
        self.features = defaultdict(float)

    def __str__(self):
        return str(self.features)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, k):
        return self.features[k]

    def __contains__(self, k):
        return k in self.features

    def __iter__(self):
        for i in self.features:
            yield i

    def get_feature_vector(self, features_mapping):
        fv = np.zeros(len(features_mapping))
        for f in self.features:
            if f in features_mapping:
                fv[features_mapping[f]] = self.features[f]

        return fv

    def get_feature_vector_lil(self, features_mapping):
        data = []
        rows = []
        for f in self.features:
            if f in features_mapping:
                data.append(self.features[f])
                rows.append(features_mapping[f])

        return data, rows

    def prune(self, remove_features):
        """
        Prune all features in the ``remove_feature`` set.

        :param remove_features: a set of features to be pruned.
        """
        for f in list(self.features.keys()):
            if f in remove_features:
                if f in self.features:
                    del self.features[f]

        # reclaim the freed memory by recreating the self.features dictionary
        self.features = dict(self.features)

    def scale(self, scale=1.0):
        """
        Scale all features with the scale.

        :param scale: the scale factor.
        """
        for f in self.features:
            self.features[f] *= scale

    def merge(self, features, weight=1.0, prefix=None):
        """
        Merges passed feature dictionary with its own features. To the features can be applied weight factor or
        the features can be added as a binary feature. If a prefix is provided, then the features are added with
        the prefixed feature name.

        :param features: a dictionary-like object with features as keys and values
        :param weight: a weight of added features with respect to already existing features. If None, then it is is added
                       as a binary feature
        :param prefix: prefix for a name of an added features, This is useful when one want to distinguish between
                       similarly generated features
        """
        if weight:
            for f in features:
                if not prefix:
                    self.features[f] += weight * features[f]
                else:
                    self.features[(prefix,)+f] += weight * features[f]
        else:
            for f in features:
                if not prefix:
                    self.features[f] = 1.0
                else:
                    self.features[(prefix,)+f] = 1.0


class UtteranceFeatures(Features):
    """
    This is a simple feature object. It is a light version of a alex.components.asr.utterance.UtteranceFeatures class.
    """

    def __init__(self, type='ngram', size=3, utterance=None):
        super(UtteranceFeatures, self).__init__()

        self.type = type
        self.size = size

        if utterance:
            self.parse(utterance)

    def parse(self, utt):
        self.features[('_bias_',)] = 1.0
        self.features[('_empty_',)] = 1.0 if not utt else 0.0

        utt = ['<s>', ] + utt.utterance + ['</s>', ]

        if self.type == 'ngram':
            for k in range(1, self.size + 1):
                for i in range(len(utt)):
                    if i + k > len(utt):
                        break

                    self.features[tuple(utt[i:i + k])] = 1.0

        new_features = defaultdict(float)
        for f in self.features:
            if len(f) == 3:
                new_features[(f[0], '*1', f[2])] = 1.0
            if len(f) == 4:
                new_features[(f[0], '*2', f[3])] = 1.0
            if len(f) == 5:
                new_features[(f[0], '*3', f[4])] = 1.0
            if len(f) == 6:
                new_features[(f[0], '*4', f[5])] = 1.0

        for f in new_features:
            self.features[f] = 1.0



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

    def __init__(self, cldb, preprocessing, features_size=4, *args, **kwargs):
        self.features_size = features_size
        self.cldb = cldb
        self.preprocessing = preprocessing

    def __repr__(self):
        r = "DAILogRegClassifier({cldb},{preprocessing},{features_size})"\
            .format(cldb=self.cldb, preprocessing=self.preprocessing, features_size=self.features_size)
        return r

    def abstract_utterance(self, utterance):
        """
        Return a list of possible abstractions of the utterance.

        :param utterance: an Utterance instance
        :return: a list of abstracted utterance, form, value, category label tuples
        """

        abs_utts = []

        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end > start:
                f = tuple(utterance[start:end])
                #print start, end
                #print f

                if f in self.cldb.form2value2cl:
                    for v in self.cldb.form2value2cl[f]:
                        for c in self.cldb.form2value2cl[f][v]:
                            u = copy.deepcopy(utterance)
                            u = u.replace2(start, end, 'CL_' + c.upper())

                            abs_utts.append((u, f, v, c))

                    #print f

                    # skip all substring for this form
                    start = end
                    break
                end -= 1
            else:
                start += 1


        return abs_utts

    def get_abstract_utterance(self, utterance, fvc):
        """
        Return an utterance with the form inn fvc abstracted to its category label

        :param utterance: an Utterance instance
        :param fvc: a form, value, category label tuple
        :return: return the abstracted utterance
        """

        form, v, c = fvc
        abs_utt = copy.deepcopy(utterance)

        if not form:
            return abs_utt

        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end > start:
                f = tuple(utterance[start:end])
                #print start, end
                #print f, form

                if f == form:
                    abs_utt = abs_utt.replace2(start, end, c)

                    # skip all substring for this form
                    start = end
                    break
                end -= 1
            else:
                start += 1

        return abs_utt

    def get_abstract_utterance2(self, utterance):
        """
        Return an utterance with the form un fvc abstracted to its category label

        :param utterance: an Utterance instance
        :return: return the abstracted utterance
        """

        abs_utt = copy.deepcopy(utterance)

        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end > start:
                f = tuple(utterance[start:end])
                #print start, end
                #print f

                if f in self.cldb.form2value2cl:
                    for v in self.cldb.form2value2cl[f]:
                        for c in self.cldb.form2value2cl[f][v]:
                            abs_utt = abs_utt.replace2(start, end, 'CL_OTHER_' + c.upper())

                    # skip all substring for this form
                    start = end
                    break
                end -= 1
            else:
                start += 1

        return abs_utt

    def get_abstract_da(self, da, fvcs):
        new_da = copy.deepcopy(da)
        c_fvcs = copy.deepcopy(fvcs)

        dai_cl_2_f_v_c = []
        for dai in new_da:
            for fvc in c_fvcs:
                f, v, c = fvc
                if dai.value == v:
                    dai.value = 'CL_' + c.upper()

                    c_fvcs.remove(fvc)
                    dai_cl_2_f_v_c.append((f, v, dai.value))
                    break
            else:
                dai_cl_2_f_v_c.append((None, None, None))

        return new_da, dai_cl_2_f_v_c

    def get_fvc_in_utterance(self, utterance):
        """
        Return a list of all form, value, category label tuples in the utterance.
        This is useful to find/guess what category label level classifiers will be necessary to instantiate.

        :param utterance: an Utterance instance
        :return: a list of form, value, and category label tuples found in the input sentence
        """

        fvcs = set()

        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end > start:
                f = tuple(utterance[start:end])

                # this looks for an exact surface form in the CLDB
                # however, we could also search for those withing a some distance from the exact surface form,
                # for example using a string edit distance
                if f in self.cldb.form2value2cl:
                    for v in self.cldb.form2value2cl[f]:
                        for c in self.cldb.form2value2cl[f][v]:
                            fvcs.add((f, v, c))

                    # skip all substring for this form
                    start = end
                    break
                end -= 1
            else:
                start += 1

        return fvcs

    def get_fvc_in_nblist(self, nblist):
        """
        Return a list of all form, value, category label tuples in the nblist.

        :param nblist: an UtteranceNBList instance
        :return: a list of form, value, and category label tuples found in the input sentence
        """

        #return self.get_fvc_in_utterance(nblist[0][1])

        fvcs = set()
        for p, u in nblist:
            fvcs.update(self.get_fvc_in_utterance(u))

        return fvcs

    def get_fvc_in_confnet(self, confnet):
        """
        Return a list of all form, value, category label tuples in the confusion network.

        :param nblist: an UtteranceConfusionNetwork instance
        :return: a list of form, value, and category label tuples found in the input sentence
        """
        nblist = confnet.get_utterance_nblist(n=CONFNET2NBLIST_EXPANSION_APPROX)

        return self.get_fvc_in_confnet(nblist)

    @lru_cache(maxsize=1000)
    def get_fvc(self, obs):
        """
        This function returns the form, value, category label tuple for any of the following classses

        - Utterance
        - UttranceNBList
        - UtteranceConfusionNetwork

        :param obs: the utterance being processed in multiple formats
        :return: a list of form, value, and category label tuples found in the input sentence
        """

        if isinstance(obs, Utterance):
            return self.get_fvc_in_utterance(obs)
        elif isinstance(obs, UtteranceNBList):
            return self.get_fvc_in_nblist(obs)
        elif isinstance(obs, UtteranceConfusionNetwork):
            return self.get_fvc_in_confnet(obs)
        else:
            raise DAILRException("Unsupported observations.")

    def get_features_in_utterance(self, utterance, fvc, fvcs):
        """
        Returns features extracted from the utterance observation. At this moment, the function extracts N-grams of size
        self.feature_size. These N-grams are extracted from:

        - the original utterance,
        - the abstracted utterance for the given FVC
        - the abstracted where all other FVCs are abstracted as well

        :param utterance:
        :param fvc:
        :return: the UtteranceFeatures instance
        """

        abs_obs = self.get_abstract_utterance(utterance, fvc)
        abs_obs2 = self.get_abstract_utterance2(abs_obs)

        feat = UtteranceFeatures(size=self.features_size)
        scale = 1.0 / 3
        feat.merge(UtteranceFeatures(size=self.features_size, utterance=utterance), weight=scale)
        feat.merge(UtteranceFeatures(size=self.features_size, utterance=abs_obs), weight=scale)
        feat.merge(UtteranceFeatures(size=self.features_size, utterance=abs_obs2), weight=scale)

        return feat

    def get_features_in_nblist(self, nblist, fvc, fvcs):
        #return self.get_features_in_utterance(nblist[0][1], fvc)

        feat = UtteranceFeatures(size=self.features_size)

        scale_p = [p for p, u in nblist]
        #scale_p[0] = 1.0

        for i, (p, u) in enumerate(nblist):
            feat.merge(self.get_features_in_utterance(u, fvc, fvcs), weight=scale_p[i])

        nbl_global = dict([ ("nbl_prob_{i}".format(i=i), p) for i, (p, h) in enumerate(nblist)])
        nbl_global["nbl_len"] = len(nblist)

        feat.merge(nbl_global)

        return feat

    def get_features_in_confnet(self, confnet, fvc, fvcs):
        nblist = confnet.get_utterance_nblist(n=CONFNET2NBLIST_EXPANSION_APPROX)
        return self.get_features_in_nblist(nblist, fvc, fvcs)

    # @lru_cache(maxsize=1000)
    def get_features(self, obs, fvc, fvcs):
        """
        Generate utterance features for a specific utterance given by utt_idx.

        :param obs: the utterance being processed in multiple formats
        :param fvc: a form, value category tuple describing how the utterance should be abstracted
        :return: a set of features from the utterance
        """

        if isinstance(obs, Utterance):
            return self.get_features_in_utterance(obs, fvc, fvcs)
        elif isinstance(obs, UtteranceNBList):
            return self.get_features_in_nblist(obs, fvc, fvcs)
        elif isinstance(obs, UtteranceConfusionNetwork):
            return self.get_features_in_confnet(obs, fvc, fvcs)
        else:
            raise DAILRException("Unsupported observations.")

    def extract_classifiers(self, das, utterances, verbose=False):
        # process the training data
        self.utterances = utterances
        self.das = das

        self.utterances_list = self.utterances.keys()

        self.utterance_fvc = {}
        self.das_abstracted = {}
        self.das_category_labels = {}
        for utt_idx in self.utterances_list:
            self.utterances[utt_idx] = self.preprocessing.normalise(self.utterances[utt_idx])
            self.utterance_fvc[utt_idx] = self.get_fvc(self.utterances[utt_idx])
            self.das_abstracted[utt_idx], self.das_category_labels[utt_idx] = \
                self.get_abstract_da(self.das[utt_idx],self.utterance_fvc[utt_idx])

        # get the classifiers
        self.classifiers = defaultdict(int)
        self.classifiers = defaultdict(int)

        for k in self.utterances_list:
            for dai in self.das_abstracted[k].dais:
                self.classifiers[unicode(dai)] += 1

                if verbose:
                    if dai.value and 'CL_' not in dai.value:
                        print '=' * 120
                        print 'Un-abstracted category label value'
                        print '-' * 120
                        print unicode(self.utterances[k])
                        print unicode(self.utterance_fvc[k])
                        print unicode(self.das[k])
                        print unicode(self.das_abstracted[k])


    def prune_classifiers(self, min_classifier_count=5):
        new_classifiers = {}
        for clser in self.classifiers:
            if '=' in clser and 'CL_' not in clser and self.classifiers[clser] < min_classifier_count:
                continue

            if '="dontcare"' in clser and '(="dontcare")' not in clser:
                continue

            if 'null()' in clser:
                continue

            new_classifiers[clser] = self.classifiers[clser]

        self.classifiers = new_classifiers


    def print_classifiers(self):
        print "=" * 120
        print "Classifiers detected in the training data"
        print "-" * 120
        print "Number of classifiers: ", len(self.classifiers)
        print "-" * 120

        for k in sorted(self.classifiers):
            print('%40s = %d' % (k, self.classifiers[k]))

    def prune_features(self, clser, min_pos_feature_count, min_neg_feature_count, verbose=False):
        if verbose:
            print 'Pruning the features'
            print

        features_counts = defaultdict(int)
        for feat in self.classifiers_features[clser]:
            for f in feat:
                features_counts[f] += 1

        if verbose:
            print "  Number of features: ", len(features_counts)


        features_counts = defaultdict(lambda: [0, 0])
        for feat, output in zip(self.classifiers_features[clser], self.classifiers_outputs[clser]):
            output = 0 if output < 0.5 else 1

            for f in feat:
                features_counts[f][output] += 1

        remove_features = []
        for f in features_counts:
            negative, positive = features_counts[f]

            if positive >= min_pos_feature_count + len(f):
                # keep it
                continue


            if negative >= min_neg_feature_count + len(f):
                # keep it
                continue

            # remove the feature since it does not meet the criteria
            remove_features.append(f)

        if verbose:
            print "  Number of features occurring less then %d positive times and %d negative times: %d" % \
                  (min_pos_feature_count, min_neg_feature_count, len(remove_features))

        remove_features = set(remove_features)
        for feat in self.classifiers_features[clser]:
            feat.prune(remove_features)


        # count the features again and report the result
        features_counts = defaultdict(int)
        for feat in self.classifiers_features[clser]:
            for f in feat:
                features_counts[f] += 1

        self.classifiers_features_list[clser] = features_counts.keys()

        self.classifiers_features_mapping[clser] = {}
        for i, f in enumerate(self.classifiers_features_list[clser]):
            self.classifiers_features_mapping[clser][f] = i

        if verbose:
            print "  Number of features after pruning: ", len(features_counts)



    def gen_classifiers_data(self, min_pos_feature_count = 5, min_neg_feature_count = 5, verbose=False, verbose2 = False):
        # generate training data
        self.classifiers_outputs = defaultdict(list)
        self.classifiers_cls = defaultdict(list)
        self.classifiers_features = defaultdict(list)
        self.classifiers_features_list = {}
        self.classifiers_features_mapping = {}


        self.parsed_classifiers = {}
        for clser in self.classifiers:
            self.parsed_classifiers[clser] = DialogueActItem()
            self.parsed_classifiers[clser].parse(clser)

        for n, clser in enumerate(sorted(self.classifiers)):
            if verbose or verbose2:
                print '=' * 120
                print 'Generating the training data for the classifier', clser , ' #', n+1 , '/', len(self.classifiers)
                print '-' * 120

            for utt_idx in self.utterances_list:
                # if verbose:
                #     print "-" * 120
                #     print unicode(self.utterances[utt_idx])
                #     print unicode(self.das[utt_idx])

                if self.parsed_classifiers[clser].value and self.parsed_classifiers[clser].value.startswith('CL_'):
                    # process abstracted classifiers
                    for i, (dai, (f, v, c)) in enumerate(zip(self.das_abstracted[utt_idx], self.das_category_labels[utt_idx])):
                        if clser == dai and self.parsed_classifiers[clser].value and self.parsed_classifiers[clser].value == c:
                            if verbose:
                                print "+ Matching a classifier in the abstracted dai, and matching category label"
                            self.classifiers_outputs[clser].append(1.0)
                            self.classifiers_cls[clser].append(self.das_category_labels[utt_idx][i])

                        elif clser != dai and self.parsed_classifiers[clser].value and self.parsed_classifiers[clser].value == c:
                            if verbose:
                                print "- NON-Matching a classifier in the abstracted dai, and matching category label"
                            self.classifiers_outputs[clser].append(0.0)
                            self.classifiers_cls[clser].append(self.das_category_labels[utt_idx][i])
                        else:
                            if verbose:
                                print "- NON-Matching a classifier in the abstracted dai, and NON-matching category label"
                            self.classifiers_outputs[clser].append(0.0)
                            self.classifiers_cls[clser].append((None, None, None))

                        self.classifiers_features[clser].append(
                            self.get_features(self.utterances[utt_idx], self.das_category_labels[utt_idx][i], self.das_category_labels[utt_idx]))

                        if verbose:
                            print "  @", clser, i, dai, f, v, c
                else:
                    # process concrete classifiers
                    if clser in self.das_abstracted[utt_idx]:
                        if verbose:
                            print "+ Matching a classifier "
                        self.classifiers_outputs[clser].append(1.0)
                        self.classifiers_cls[clser].append((None, None, None))
                    else:
                        if verbose:
                            print "- NON-Matching a classifier"
                        self.classifiers_outputs[clser].append(0.0)
                        self.classifiers_cls[clser].append((None, None, None))

                    self.classifiers_features[clser].append(self.get_features(self.utterances[utt_idx], (None, None, None), self.das_category_labels[utt_idx]))

                    if verbose:
                        print "  @", clser

            self.classifiers_outputs[clser] = np.array(self.classifiers_outputs[clser])

            if verbose:
                print clser
                print zip(self.classifiers_outputs[clser], self.classifiers_cls[clser])

            self.prune_features(clser, min_pos_feature_count, min_neg_feature_count, verbose = (verbose or verbose2))

    def train(self, inverse_regularisation=1.0, verbose=True):
        self.trained_classifiers = {}

        if verbose:
            print '=' * 120
            print 'Training'

        for n, clser in enumerate(sorted(self.classifiers)):
            if verbose:
                print '-' * 120
                print "Training classifier: ", clser, ' #', n+1 , '/', len(self.classifiers)
                print "  Matrix:            ", (len(self.classifiers_outputs[clser]), len(self.classifiers_features_list[clser]))

            classifier_input = np.zeros((len(self.classifiers_outputs[clser]), len(self.classifiers_features_list[clser])))
            for i, feat in enumerate(self.classifiers_features[clser]):
                classifier_input[i] = feat.get_feature_vector(self.classifiers_features_mapping[clser])

            lr = LogisticRegression('l2', C=inverse_regularisation, tol=1e-6)

            lr.fit(classifier_input, self.classifiers_outputs[clser])
            self.trained_classifiers[clser] = lr

            if verbose:
                mean_accuracy = lr.score(classifier_input, self.classifiers_outputs[clser])
                print "  Prediction mean accuracy on the training data: %6.2f" % (100.0 * mean_accuracy, )
                print "  Size of the params:", lr.coef_.shape


    def save_model(self, file_name, gzip=None):
        data = [self.classifiers_features_list, self.classifiers_features_mapping, self.trained_classifiers,
                self.parsed_classifiers, self.features_size]

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
            (self.classifiers_features_list, self.classifiers_features_mapping, self.trained_classifiers,
             self.parsed_classifiers, self.features_size) = pickle.load(model_file)

    def parse_X(self, utterance, verbose=False):
        if verbose:
            print '='*120
            print 'Parsing X'
            print '-'*120
            print unicode(utterance)

        if self.preprocessing:
            utterance = self.preprocessing.normalise(utterance)
            utterance_fvcs = self.get_fvc(utterance)

        if verbose:
            print unicode(utterance)
            print unicode(utterance_fvcs)


        da_confnet = DialogueActConfusionNetwork()
        for clser in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", unicode(clser)

            if self.parsed_classifiers[clser].value and self.parsed_classifiers[clser].value.startswith('CL_'):
                # process abstracted classifiers

                for f, v, c in utterance_fvcs:
                    cc = "CL_" + c.upper()

                    if self.parsed_classifiers[clser].value == cc:
                        #print clser, f, v, c

                        classifiers_features = self.get_features(utterance, (f, v, cc), utterance_fvcs)
                        classifiers_inputs = np.zeros((1, len(self.classifiers_features_mapping[clser])))
                        classifiers_inputs[0] = classifiers_features.get_feature_vector(self.classifiers_features_mapping[clser])

                        #if verbose:
                        #    print classifiers_features
                        #    print self.classifiers_features_mapping[clser]

                        p = self.trained_classifiers[clser].predict_proba(classifiers_inputs)

                        if verbose:
                            print '  Probability:', p

                        dai = DialogueActItem(self.parsed_classifiers[clser].dat, self.parsed_classifiers[clser].name, v)
                        da_confnet.add_merge(p[0][1], dai, combine='max')
            else:
                # process concrete classifiers
                classifiers_features = self.get_features(utterance, (None, None, None), utterance_fvcs)
                classifiers_inputs = np.zeros((1, len(self.classifiers_features_mapping[clser])))
                classifiers_inputs[0] = classifiers_features.get_feature_vector(self.classifiers_features_mapping[clser])

                #if verbose:
                #    print classifiers_features
                #    print self.classifiers_features_mapping[clser]

                p = self.trained_classifiers[clser].predict_proba(classifiers_inputs)

                if verbose:
                    print '  Probability:', p

                dai = self.parsed_classifiers[clser]
                da_confnet.add_merge(p[0][1], dai, combine='max')

        da_confnet.sort().prune()

        return da_confnet

    def parse_1_best(self, obs=dict(), ret_cl_map=False, verbose=False, *args, **kwargs):
        """
        Parse ``utterance`` and generate the best interpretation in the form of
        a dialogue act (an instance of DialogueAct).

        The result is the dialogue act confusion network.

        """

        utterance = obs['utt']

        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        return self.parse_X(utterance, verbose)

    def parse_nblist(self, obs, verbose=False, *args, **kwargs):
        """
        Parses n-best list by parsing each item on the list and then merging
        the results.
        """

        utterance_list = obs['utt_nbl']
        if len(utterance_list) == 0:
            raise DAILRException("Empty utterance N-best list.")

        return self.parse_X(utterance_list, verbose)

    def parse_confnet(self, obs, verbose=False, *args, **kwargs):
        """
        Parses the word confusion network by generating an n-best list and
        parsing this n-best list.
        """
        confnet = obs['utt_cn']
        return self.parse_X(confnet, verbose)
