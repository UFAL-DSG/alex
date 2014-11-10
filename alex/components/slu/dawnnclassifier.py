#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a rewrite of the DAILogRegClassifier. This code uses Theano FFNN.
"""
from __future__ import unicode_literals

import copy
import numpy as np
import cPickle as pickle

from collections import defaultdict
from scipy.sparse import lil_matrix

from alex.components.asr.utterance import Utterance, UtteranceHyp, UtteranceNBList, UtteranceConfusionNetwork
from alex.components.slu.exceptions import DAILRException
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork
from alex.ml import twffnn as tffnn
from alex.utils.cache import lru_cache
from alex.utils.czech_stemmer import cz_stem_word

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
        # positive feature vector
        fv = np.zeros(len(features_mapping), dtype=np.float32)
        # negative feature vector        
        fv_neg = np.zeros(len(features_mapping), dtype=np.float32)

        for f in features_mapping:
            if f in self.features:
                fv[features_mapping[f]] = self.features[f]
            else:
                fv_neg[features_mapping[f]] = 1.0

        return fv
        # return np.hstack((fv, fv_neg))

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
                    self.features[(prefix,) + f] += weight * features[f]
        else:
            for f in features:
                if not prefix:
                    self.features[f] = 1.0
                else:
                    self.features[(prefix,) + f] = 1.0


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


class DANNClassifier(SLUInterface):
    """Implements learning of dialogue act classifiers using NN classifier.

    The parser implements a parser based on set of classifiers for each
    dialogue act item. When parsing the input utterance, the parse classifies
    whether a given dialogue act item is present. Then, the output dialogue
    act is composed of all detected dialogue act items.

    Dialogue act is defined as a composition of dialogue act items. E.g.

    confirm(drinks="wine")&inform(name="kings shilling") <=> 'does kings serve wine'

    where confirm(drinks="wine") and inform(name="kings shilling") are two
    dialogue act items.

    This parser uses neural network with binary outputs as the classifiers of the dialogue
    act items.

    """

    def __init__(self, cldb, preprocessing, features_size=4, *args, **kwargs):
        self.features_size = features_size
        self.cldb = cldb
        self.preprocessing = preprocessing

    def __repr__(self):
        r = "DANNClassifier({cldb},{preprocessing},{features_size})" \
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
                # print start, end
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
                # print start, end
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
                # print start, end
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

    def get_abstract_utterance3(self, utterance, fvcs):
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
                form = tuple(utterance[start:end])
                # print start, end
                #print f

                for f, v, c in fvcs:
                    if form == f:
                        abs_utt = abs_utt.replace2(start, end, c)

                        # skip all substring for this form
                        start = end
                        break

                end -= 1
            else:
                start += 1

        return abs_utt

    def get_abstract_utterance_da(self, da, cls):
        abs_da = copy.deepcopy(da)

        for cl_name in category_labels:
            for dai in da:
                if dai.value == category_labels[cl][1]:
                    dai.value = cl_name
                    break

        return abs_da

    def get_abstract_da(self, da, fvcs):
        """
        	Returns an abstracted dialogie act and used abstractions in abstraction.
        """
        new_da = copy.deepcopy(da)
        c_fvcs = copy.deepcopy(fvcs)

        dai_cl_2_f_v_c = []
        for dai in new_da:
            for fvc in c_fvcs:
                f, v, c = fvc
                if dai.value == v:
                    dai.value = c

                    c_fvcs.remove(fvc)
                    dai_cl_2_f_v_c.append((f, v, c))
                    break
            else:
                dai_cl_2_f_v_c.append((None, None, None))

        return new_da, dai_cl_2_f_v_c

    def get_fvc_in_utterance(self, utterance, category_label_counter=None, category_labels=None):
        """
        Return a list of all form, value, category label tuples in the utterance.
        This is useful to find/guess what category label level classifiers will be necessary to instantiate.

        :param utterance: an Utterance instance
        :return: a list of form, value, and category label tuples found in the input sentence
        """

        fvcs = set()

        if category_label_counter == None and category_labels == None:
            category_label_counter = defaultdict(int)
            category_labels = {}

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
                            if c == 'number':
                                if end < len(utterance) and \
                                   utterance[start] == 'půl' and \
                                   utterance[start+1] == 'hodiny':
                                    c = 'time'
                                    v = '0:30'
                                elif end < len(utterance)-1 and \
                                   utterance[end] in set(['hodina', 'hodin', 'hodiny', 'hodinu', 'hodinou', 'ráno', 'dopoledne', 'odpoledne', 'večer']) and \
                                   utterance[end+1] not in set(['a',]):
                                    c = 'time'
                                    v += ':00'
                                elif end < len(utterance)-1 and \
                                   utterance[end] == 'nula' and \
                                   utterance[end+1] == 'nula':
                                    c = 'time'
                                    v += ':00'
                                elif end < len(utterance) and \
                                   utterance[end] == 'třicet':
                                    c = 'time'
                                    v += ':30'
                                elif end < len(utterance)-1 and \
                                   utterance[end] in set(['hodina', 'hodin', 'hodiny', 'hodinu']) and \
                                   utterance[end+1] == 'třicet':
                                    c = 'time'
                                    v += ':30'
                                elif end < len(utterance)-1 and \
                                   utterance[end] == 'čtyřicet' and \
                                   utterance[end+1] == 'pět':
                                    c = 'time'
                                    v += ':45'
                                elif end == len(utterance)-1 and \
                                   utterance[end] in set(['hodina', 'hodin', 'hodiny', 'hodinu', 'hodinou', 'ráno', 'dopoledne', 'odpoledne', 'večer']):
                                    c = 'time'
                                    v += ':00'
                                elif end == len(utterance) and \
                                   utterance[start-1] in set(['v', ]):
                                    c = 'time'
                                    v += ':00'
                                elif end <= len(utterance) and \
                                   utterance[start-1] in set(['za', ]) and \
                                   utterance[end] in set(['minut', ]) :
                                    c = 'time'
                                    v = '0:'+v
                      
                            cl_name = 'CL_' + c.upper() + '-' + unicode(category_label_counter[c])
                            category_label_counter[c] += 1

                            fvcs.add((f, v, cl_name))

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

        # return self.get_fvc_in_utterance(nblist[0][1])

        category_label_counter = defaultdict(int)
        category_labels = {}

        fvcs = set()
        for p, u in nblist:
            fvcs.update(self.get_fvc_in_utterance(u, category_label_counter, category_labels))

        return fvcs

    def get_fvc_in_confnet(self, confnet):
        """
        Return a list of all form, value, category label tuples in the confusion network.

        :param nblist: an UtteranceConfusionNetwork instance
        :return: a list of form, value, and category label tuples found in the input sentence
        """
        nblist = confnet.get_utterance_nblist(n=CONFNET2NBLIST_EXPANSION_APPROX)

        return self.get_fvc_in_nblist(nblist)

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

    def get_features_in_utterance(self, utterance, fvcs):
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

        abs_obs = self.get_abstract_utterance3(utterance, fvcs)

        feat = UtteranceFeatures(size=self.features_size)
        scale = 1.0 / 2
        feat.merge(UtteranceFeatures(size=self.features_size, utterance=utterance), weight=scale)
        feat.merge(UtteranceFeatures(size=self.features_size, utterance=abs_obs), weight=scale)

        return feat

    def get_features_in_nblist(self, nblist, fvcs):
        # return self.get_features_in_utterance(nblist[0][1], fvc)

        feat = UtteranceFeatures(size=self.features_size)

        scale_p = [p for p, u in nblist]
        #scale_p[0] = 1.0

        for i, (p, u) in enumerate(nblist):
            feat.merge(self.get_features_in_utterance(u, fvcs), weight=scale_p[i])

        nbl_global = dict([("nbl_prob_{i}".format(i=i), p) for i, (p, h) in enumerate(nblist)])
        nbl_global["nbl_len"] = len(nblist)

        feat.merge(nbl_global)

        return feat

    def get_features_in_confnet(self, confnet, fvcs):
        nblist = confnet.get_utterance_nblist(n=CONFNET2NBLIST_EXPANSION_APPROX)
        return self.get_features_in_nblist(nblist, fvcs)

    def get_features(self, obs, fvcs):
        """
        Generate utterance features for a specific utterance given by utt_idx.

        :param obs: the utterance being processed in multiple formats
        :param fvc: a form, value category tuple describing how the utterance should be abstracted
        :return: a set of features from the utterance
        """

        if isinstance(obs, Utterance):
            return self.get_features_in_utterance(obs, fvcs)
        elif isinstance(obs, UtteranceNBList):
            return self.get_features_in_nblist(obs, fvcs)
        elif isinstance(obs, UtteranceConfusionNetwork):
            return self.get_features_in_confnet(obs, fvcs)
        else:
            raise DAILRException("Unsupported observations.")

    def get_wfeatures_in_utterance(self, utterance, fvcs, utterance_size):
        """
        """

        u = ['U_START',]+list(utterance)
        for x in range(utterance_size - len(u)):
            u.append('U_END')

        abs_utt = self.get_abstract_utterance3(utterance, fvcs)
        a = ['A_START',]+list(abs_utt)
        for x in range(utterance_size - len(a)):
            a.append('A_END')

#        u = u[:utterance_size]
        u = []
        u.extend(a[:utterance_size])

        return u
        
    def get_wfeatures(self, obs, fvcs, utterance_size):
        """
        Generate utterance features for a specific utterance given by utt_idx.

        :param obs: the utterance being processed in multiple formats
        :param fvc: a form, value category tuple describing how the utterance should be abstracted
        :return: a set of features from the utterance
        """

        if isinstance(obs, Utterance):
            return self.get_wfeatures_in_utterance(obs, fvcs, utterance_size)
        elif isinstance(obs, UtteranceNBList):
            return self.get_wfeatures_in_nblist(obs, fvcs)
        elif isinstance(obs, UtteranceConfusionNetwork):
            return self.get_wfeatures_in_confnet(obs, fvcs)
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
                self.get_abstract_da(self.das[utt_idx], self.utterance_fvc[utt_idx])

        # get the classifiers
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

        self.classifiers_list = sorted(self.classifiers.keys())

    def prune_classifiers(self, min_classifier_count=5):
        new_classifiers = {}
        for clser in self.classifiers:
            if '=' in clser and 'CL_' not in clser and self.classifiers[clser] < min_classifier_count:
                continue

            if '=' in clser and 'CL_' in clser and self.classifiers[clser] <= 1:
                 continue

            if '="dontcare"' in clser and '(="dontcare")' not in clser:
                continue

            if 'null()' in clser:
                continue

            new_classifiers[clser] = self.classifiers[clser]

        self.classifiers = new_classifiers
        self.classifiers_list = sorted(self.classifiers.keys())

    def print_classifiers(self):
        print "=" * 120
        print "Classifiers detected in the training data"
        print "-" * 120
        print "Number of classifiers: ", len(self.classifiers)
        print "-" * 120

        for clser in self.classifiers_list:
            print('%40s = %d' % (clser, self.classifiers[clser]))

    def prune_features(self, classifier_features, min_pos_feature_count, min_neg_feature_count, verbose=False):
        print 'Pruning the features'
        print

        features_counts = defaultdict(int)
        for feat in classifier_features:
            for f in feat:
                features_counts[f] += 1

        if verbose:
            print "  Number of features: ", len(features_counts)

        features_counts = defaultdict(lambda: [0, 0])
        for clser in self.classifiers_outputs:
            for feat, output in zip(classifier_features, self.classifiers_outputs[clser]):
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
        for feat in classifier_features:
            feat.prune(remove_features)


        # count the features again and report the result
        features_counts = defaultdict(int)
        for feat in classifier_features:
            for f in feat:
                features_counts[f] += 1

        self.classifiers_features_list = features_counts.keys()

        self.classifiers_features_mapping = {}
        for i, f in enumerate(self.classifiers_features_list):
            self.classifiers_features_mapping[f] = i

        if verbose:
            print "  Number of features after pruning: ", len(features_counts)

    def gen_vocabulary(self, classifier_features, min_word_count=2):
    
        words = defaultdict(int)
        for u in classifier_features:
            for w in u:
                words[w] += 1

        print "Words before pruning", len(words)
            
        self.classifiers_features_list = ['OOV',]
        for w in sorted(words.keys()):
            if words[w] >= min_word_count:
                self.classifiers_features_list.append(w)

        for i, f in enumerate(self.classifiers_features_list):
            self.classifiers_features_mapping[f] = i

        print "Words after pruning", len(self.classifiers_features_list)
        
    def map_words_to_ints(self, ulist):
        r = []
        for w in ulist:
            if w in self.classifiers_features_mapping:
                r.append(self.classifiers_features_mapping[w])
            else:
                r.append(self.classifiers_features_mapping['OOV'])
        return r    
        
                
    def gen_classifiers_data(self, min_pos_feature_count=5, min_neg_feature_count=5, verbose=False, verbose2=False,
                             fn_pickle=None,
                             full_abstraction=True,
                             utterance_size = 10):
        try:
            print 'Reading', fn_pickle
            with open(fn_pickle, "rb") as f:
                self.classifier_output = np.load(f)
                self.classifier_input = np.load(f)
                self.utterance_size, \
                self.classifiers_list, \
                self.classifiers_features_list, \
                self.classifiers_features_mapping, \
                self.parsed_classifiers = pickle.load(f)

                if verbose2:
                    print '-' * 120
                    print "Input classifier matrix:  ", self.classifier_input.shape
                    print "Output classifier matrix: ", self.classifier_output.shape
                    print "#Classifiers:             ", len(self.classifiers_list)
                    print "Utterance size:           ", self.utterance_size
                    print "Vocabulary size:          ", len(self.classifiers_features_list)
                return
        except IOError:
            print 'No existing pickle', fn_pickle
            pass

        self.utterance_size = utterance_size
        
        # generate training data for the train and pars functions
        self.classifiers_outputs = defaultdict(list)
        self.classifiers_inputs = defaultdict(list)
        self.classifiers_features_list = {}
        self.classifiers_features_mapping = {}
        self.parsed_classifiers = {}
        for clser in self.classifiers:
            self.parsed_classifiers[clser] = DialogueActItem()
            self.parsed_classifiers[clser].parse(clser)

        classifier_features = []

        if (verbose or verbose2):
            print '=' * 120

        for n, utt_idx in enumerate(self.utterances_list):
            if (verbose or verbose2) and n % (len(self.utterances_list) / 10) == 0:
                print 'Generating the training data for the utterance #', n + 1, '/', len(self.utterances_list)

            if not full_abstraction:
                classifier_features.append(self.get_wfeatures(self.utterances[utt_idx], self.das_category_labels[utt_idx], self.utterance_size))
            else:
               # WARNING: BING Thing even for log reg.
               classifier_features.append(self.get_wfeatures(self.utterances[utt_idx], self.utterance_fvc[utt_idx], self.utterance_size))

            for clser in self.classifiers:
                if verbose:
                    print "-" * 120
                    print unicode(self.utterances[utt_idx])
                    print unicode(self.utterance_fvc[utt_idx])
                    print unicode(clser)
                    print unicode(self.das[utt_idx])
                    print unicode(self.das_abstracted[utt_idx])

                if clser in self.das_abstracted[utt_idx]:
                    if verbose:
                        print "+ Matching a classifier "
                    self.classifiers_outputs[clser].append((1.0,))
                else:
                    if verbose:
                        print "- NON-Matching a classifier"
                    self.classifiers_outputs[clser].append((0.0,))

        for clser in self.classifiers:
            self.classifiers_outputs[clser] = np.array(self.classifiers_outputs[clser], dtype=np.float32)

#        self.prune_features(classifier_features, min_pos_feature_count, min_neg_feature_count,
#                            verbose=(verbose or verbose2))

        self.gen_vocabulary(classifier_features, min_word_count=min_pos_feature_count)

#        self.classifier_input = np.zeros((len(classifier_features), 2*utterance_size),dtype=np.int32)
        self.classifier_input = np.zeros((len(classifier_features), utterance_size),dtype=np.int32)
        for i, feat in enumerate(classifier_features):
            self.classifier_input[i] = self.map_words_to_ints(feat)

        o = np.hstack([self.classifiers_outputs[clser] for clser in self.classifiers_list])
        self.classifier_output = np.hstack((o, 1 - o))

        if verbose2:
            print '-' * 120
            print "Input classifier matrix:  ", self.classifier_input.shape
            print "Output classifier matrix: ", self.classifier_output.shape
            print "#Classifiers:             ", len(self.classifiers_list)
            print "Utterance size:           ", self.utterance_size
            print "Vocabulary size:          ", len(self.classifiers_features_list)

        with open(fn_pickle, "wb") as f:
            print 'Writing', fn_pickle
            np.save(f, self.classifier_output)
            np.save(f, self.classifier_input)
            data = (self.utterance_size, \
                    self.classifiers_list,
                    self.classifiers_features_list,
                    self.classifiers_features_mapping,
                    self.parsed_classifiers)
            pickle.dump(data, f)

    def scoring(self, case, pred):
        """
        :param case:
        :param pred:
        :return:
        """

        # TN / True Negative: case was negative and predicted negative
        tn = float(np.sum(np.logical_and(case < 0.5, pred < 0.5)))
        # TP / True Positive: case was positive and predicted positive
        tp = float(np.sum(np.logical_and(case >= 0.5, pred >= 0.5)))
        # FN / False Negative: case was positive but predicted negative
        fn = float(np.sum(np.logical_and(case >= 0.5, pred < 0.5)))
        # FP / False Positive: case was negative but predicted positive
        fp = float(np.sum(np.logical_and(case < 0.5, pred >= 0.5)))

        acc = (tp + tn) / (tp + tn + fp + fn)
        pre = tp / (tp + fp) if tp + fp > 1 else 0.0
        rec = tp / (tp + fn) if tp + fp > 1 else 0.0
        fme = 2 * pre * rec / (pre + rec) if pre + rec > 1e-6 else 0.0

        return acc, fme, pre, rec

    def train(self,
              weight_alpha=None,
              method='sg-fixedlr',
              hact='tanh',
              learning_rate=500e-3,
              learning_rate_decay=1000.0,
              n_hidden_units=0,
              n_hidden_layers=0,
              n_epoch=300,
              n_batches=1000,
              embedding_size=10,
              max_pooling=False,
              move_training_set_to_GPU=False,
              standardize=False,
              gradient_treatment='normalisation',
              crossvalidation=False,
              verbose=True):
        if verbose:
            print '=' * 120
            print 'Training'
            print '  Embedding size:', embedding_size
            print '-' * 120


        indices = np.random.permutation(self.classifier_input.shape[0])
        if crossvalidation:
            training_data_size = int(0.9 * len(indices))
        else:
            training_data_size = len(indices)
        training_idx, test_idx = indices[:training_data_size], indices[training_data_size:]
        training_input, crossvalid_input = self.classifier_input[training_idx, :], self.classifier_input[test_idx, :]
        training_output, crossvalid_output = self.classifier_output[training_idx, :], self.classifier_output[test_idx, :]

        if weight_alpha:
            weight_bias = np.reciprocal(np.mean(self.classifier_output, axis=0))
            weight_bias = (1.0 - weight_alpha) * np.ones_like(weight_bias) + weight_alpha * weight_bias
#            for i in range(len(weight_bias) / 2, len(weight_bias)):
#                weight_bias[i] = 1.0
        else:
            weight_bias = None

        batch_size = training_input.shape[0] / n_batches + 1

        nn = tffnn.TheanoFFNN(training_input.shape[1], n_hidden_units, n_hidden_layers, training_output.shape[1],
                              hidden_activation=hact, weight_l2=1e-6,
                              training_set_x=training_input, training_set_y=training_output,
                              batch_size=batch_size,
                              classifier='binary-set',
                              weight_bias=weight_bias,
                              gradient_treatment=gradient_treatment,
                              g_max=1e+3,
                              move_training_set_to_GPU=move_training_set_to_GPU,
                              embedding_size=embedding_size,
                              max_pooling=max_pooling,
                              vocabulary_size=len(self.classifiers_features_mapping))

        max_crossvalid_fme = 0.0
        n_no_icrease_on_crossvalid = 0
        for epoch in range(n_epoch):
            print "Epoch", epoch

            predictions_y = nn.predict(training_input, batch_size=batch_size/10)

            t_acc, t_fme, t_pre, t_rec = self.scoring(training_output[:, :training_output.shape[1] / 2],
                                                      predictions_y[:, :training_output.shape[1] / 2])

            print "  Prediction on the training data (data size):", training_input.shape
            print "    Accuracy:  %6.4f" % (t_acc * 100.0,)
            print "    Precision: %6.4f" % (t_pre * 100.0,)
            print "    Recall:    %6.4f" % (t_rec * 100.0,)
            print "    F-measure: %6.4f" % (t_fme * 100.0,)
            print "    ------------------------------------------"
            print "    t %10.8f p %10.8f" % (
                np.mean(training_output[:, :training_output.shape[1] / 2] >= 0.5) * 100.0,
                np.mean(predictions_y[:, :training_output.shape[1] / 2] >= 0.5) * 100.0)

            if crossvalidation:
                predictions_y = nn.predict(crossvalid_input, batch_size=batch_size/10)
                c_acc, c_fme, c_pre, c_rec = self.scoring(crossvalid_output[:, :crossvalid_output.shape[1] / 2],
                                                          predictions_y[:, :crossvalid_output.shape[1] / 2])

                print "  Prediction on the training data (data size):", crossvalid_input.shape
                print "    Accuracy:  %6.4f" % (c_acc * 100.0,)
                print "    Precision: %6.4f" % (c_pre * 100.0,)
                print "    Recall:    %6.4f" % (c_rec * 100.0,)
                print "    F-measure: %6.4f" % (c_fme * 100.0,)
                print "    ------------------------------------------"
                print "    t %10.8f p %10.8f" % (
                    np.mean(crossvalid_output[:, :training_output.shape[1] / 2] >= 0.5) * 100.0,
                    np.mean(predictions_y[:, :training_output.shape[1] / 2] >= 0.5) * 100.0)
            else:
                c_fme = t_fme
                print "  WARNING: Instead of crossvalidation data, training data are used!"


            if max_crossvalid_fme + 0.0001 < c_fme:
                print "  Storing the best classifiers so far"
                self.trained_classifier = nn
                max_crossvalid_fme = c_fme
                n_no_icrease_on_crossvalid = 0
            else:
                n_no_icrease_on_crossvalid += 1
                print "  Worse than the best classifiers"
                print "        The best classifiers FME: %6.4f" % (max_crossvalid_fme * 100.0,)

            print "  Number of iterations with no increase on crossvalid data:", n_no_icrease_on_crossvalid

            if n_no_icrease_on_crossvalid >= 40:
                print "  Stop: It does not have to be better - reached the max n_no_icrease_on_crossvalid"
                break

            if c_fme >= 0.99 or max_crossvalid_fme >= 0.99:
                print "  Stop: It does not have to be better - reached the max acc"
                break

            print "  Training "
            nn.train(method=method, learning_rate=learning_rate * learning_rate_decay / (learning_rate_decay + epoch))

    def save_model(self, file_name, gzip=None):
        data = (self.classifiers_list,
                self.classifiers_features_list,
                self.classifiers_features_mapping,
                self.trained_classifier.get_params(),
                self.parsed_classifiers,
                self.features_size,
                self.utterance_size)

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
            (self.classifiers_list,
             self.classifiers_features_list,
             self.classifiers_features_mapping,
             trained_classifier_params,
             self.parsed_classifiers,
             self.features_size,
             self.utterance_size) = pickle.load(model_file)

        self.trained_classifier = tffnn.TheanoFFNN()
        self.trained_classifier.set_params(trained_classifier_params)

    def parse_X(self, utterance, verbose=False):
        #verbose = True

        if verbose:
            print '=' * 120
            print 'Parsing X'
            print '-' * 120
            print unicode(utterance)

        if self.preprocessing:
            utterance = self.preprocessing.normalise(utterance)
            utterance_fvcs = self.get_fvc(utterance)

        if verbose:
            print unicode(utterance)
            print unicode(utterance_fvcs)

        classifier_features = self.get_wfeatures(utterance, utterance_fvcs, self.utterance_size)
#        classifier_input = np.zeros((1, 2*self.utterance_size), dtype=np.int32)
        classifier_input = np.zeros((1, self.utterance_size), dtype=np.int32)
        classifier_input[0] = self.map_words_to_ints(classifier_features)
    
        
        if verbose:
            print classifier_features
            print classifier_input
        #            print self.classifiers_features_mapping

        da_prob = self.trained_classifier.predict(classifier_input)

        if verbose:
            print da_prob.shape
            print '  DA probability 1:', da_prob[:, :da_prob.shape[1] / 2]
            print '  DA probability 0:', da_prob[:, da_prob.shape[1] / 2:]

        da_confnet = DialogueActConfusionNetwork()
        for n, clser in enumerate(self.classifiers_list):
            if verbose:
                print "Using classifier: ", unicode(clser)

            if self.parsed_classifiers[clser].value and self.parsed_classifiers[clser].value.startswith('CL_'):
                # process abstracted classifiers

                for f, v, c in utterance_fvcs:
                    if self.parsed_classifiers[clser].value == c:
                        if verbose:
                            print clser, f, v, c

                        dai_prob = da_prob[0][n]

                        if verbose:
                            print '  Probability:', dai_prob

                        dai = DialogueActItem(self.parsed_classifiers[clser].dat, self.parsed_classifiers[clser].name,
                                              v)
                        da_confnet.add(dai_prob, dai)
            else:
                #if verbose:
                #    print classifiers_features
                #    print self.classifiers_features_mapping[clser]

                dai_prob = da_prob[0][n]

                if verbose:
                    print '  Probability:', dai_prob

                da_confnet.add(dai_prob, self.parsed_classifiers[clser])

        da_confnet.sort().merge().prune()

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
