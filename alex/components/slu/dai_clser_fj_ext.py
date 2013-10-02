#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a rewrite of the DAILogRegClassifier ``from dai_clser_fj.py``. The underlying approach is the same; however,
the way how the features are computed is changed significantly. Therefore, all classes including those ``from base_fj.py``
are defined here just so emphasize that these are designed to support this classifier.
"""
from __future__ import unicode_literals

import copy
import numpy as np
import cPickle as pickle

from collections import defaultdict
from sklearn.linear_model import LogisticRegression

from alex.components.asr.utterance import Utterance, UtteranceHyp, UtteranceNBList, UtteranceConfusionNetwork
from alex.components.slu.exceptions import SLUException, DAILRException
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork, merge_slu_confnets
from alex.utils.config import load_as_module
from alex.utils.various import nesteddict


class CategoryLabelDatabase(object):
    """ Provides a convenient interface to a database of category label value forms tuples.

    Attributes:
          form_value_category: a list of (form, value, category label) tuples

    """

    def __init__(self, file_name):
        self.database = {}
        self.forms = []
        self.form_value_cl = []
        self.form2value2cl = nesteddict()

        if file_name:
            self.load(file_name)

    def __iter__(self):
        """Yields tuples (form, value, category label) from the database."""

        for i in self.form_value_cl:
            yield i

    def load(self, file_name):
        """
        Load the database with category labels, values, and forms from a file.

        :param file_name: a file name of a the category label database file

        """

        db_mod = load_as_module(file_name, force=True)
        if not hasattr(db_mod, 'database'):
            raise SLUException("The category label database does not define the `database' object!")
        self.database = db_mod.database

        self.normalise_database()
        # Update derived data structures.
        self.gen_form_value_cl_list()
        self.gen_mapping_form2value2cl()


    def normalise_database(self):
        """Normalise database. E.g. split utterances into sequences of words.
        """
        new_db = dict()
        for name in self.database:
            new_db[name] = dict()
            for value in self.database[name]:
                new_db[name][value] = [tuple(form.split()) for form in self.database[name][value]]
        self.database = new_db


    def gen_form_value_cl_list(self):
        """
        Generates an list of form, value, category label tuples from the database. This list is ordered where the tuples
        with the longest surface forms are at the beginning of the list.

        :return: none
        """
        for cl in self.database:
            for value in self.database[cl]:
                for form in self.database[cl][value]:
                    self.form_value_cl.append((form, value, cl))

        self.form_value_cl.sort(key=lambda fvc: len(fvc[0]), reverse=True)

    def gen_mapping_form2value2cl(self):
        """
        Generates an list of form, value, category label tuples from the database . This list is ordered where the tuples
        with the longest surface forms are at the beginning of the list.

        :return: none
        """

        for cl in self.database:
            for value in self.database[cl]:
                for form in self.database[cl][value]:
                    self.form2value2cl[form][value][cl] = 1
                    self.forms.append(form)

        self.forms.sort(key=lambda f: len(f), reverse=True)


class Features(object):
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

    def prune(self, remove_features):
        for f in list(self.set):
            if f in remove_features:
                self.set.discard(f)

                if f in self.features:
                    del self.features[f]

    def scale(self, scale=1.0):
        for f in self.features:
            self.features[f] *= scale

    def merge(self, features, weight=1.0):
        for f in features:
            self.features[f] += weight * features[f]

        self.set = set(self.features.keys())


class UtteranceFeatures(Features):
    def __init__(self, type='ngram', size=3, utterance=None):
        super(UtteranceFeatures, self).__init__()

        self.type = type
        self.size = size

        if utterance:
            self.parse(utterance)

    def parse(self, utt):
        self.features['_empty_'] = 1.0 if not utt else 0.0

        utt = ['<s>', ] + utt.utterance + ['</s>', ]

        if self.type == 'ngram':
            for k in range(1, self.size + 1):
                for i in range(len(utt)):
                    if i + k > len(utt):
                        break

                    self.features[tuple(utt[i:i + k])] += 1.0

        new_features = defaultdict(float)
        for f in self.features:
            if len(f) == 3:
                new_features[(f[0], '*1', f[2])] += 1.0
            if len(f) == 4:
                new_features[(f[0], '*2', f[3])] += 1.0
            if len(f) == 5:
                new_features[(f[0], '*3', f[4])] += 1.0
            if len(f) == 6:
                new_features[(f[0], '*4', f[4])] += 1.0

        for f in new_features:
            self.features[f] += new_features[f]

        self.set = set(self.features.keys())


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
        self.preprocessing = preprocessing
        self.cldb = cldb

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
                    break
                end -= 1
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

                    break
                end -= 1
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

                    break
                end -= 1
            start += 1
        return abs_utt

    def get_abstract_das(self, da, fvcs):
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

                    break
                end -= 1
            start += 1

        return fvcs

    def get_fvc_in_nblist(self, nblist):
        """
        Return a list of all form, value, category label tuples in the nblist.

        :param nblist: an UtteranceNBList instance
        :return: a list of form, value, and category label tuples found in the input sentence
        """
        pass

    def get_fvc_in_confnet(self, confnet):
        """
        Return a list of all form, value, category label tuples in the confusion network.

        :param nblist: an UtteranceConfusionNetwork instance
        :return: a list of form, value, and category label tuples found in the input sentence
        """
        pass

    def get_fvc(self, obs):
        """

        :param obs: the utterance being processed in multiple formats
        :return: a list of form, value, and category label tuples found in the input sentence
        """
        if isinstance(obs, Utterance):
            return self.get_fvc_in_utterance(obs)
        elif isinstance(obs, UtteranceConfusionNetwork):
            return self.get_fvc_in_confnet(obs)
        elif isinstance(obs, UtteranceNBList):
            return self.get_fvc_in_nblist(obs)
        else:
            raise DAILRException("Unsupported observations.")

    def get_features_in_utterance(self, obs, fvc):
        abs_obs = self.get_abstract_utterance(obs, fvc)
        abs_obs2 = self.get_abstract_utterance2(abs_obs)
        #stem_obs =  Utterance(" ".join(map(cz_stem, obs)))
        #abs_stem_obs = self.get_abstract_utterance(stem_obs, fvc)
        #abs_stem_obs2 = self.get_abstract_utterance2(stem_abs_obs)

        scale = 1.0 / 3
        feat = UtteranceFeatures(size=self.features_size, utterance=obs)
        feat.scale(scale)
        feat.merge(UtteranceFeatures(size=self.features_size, utterance=abs_obs), weight=scale)
        feat.merge(UtteranceFeatures(size=self.features_size, utterance=abs_obs2), weight=scale)
        #feat.merge(UtteranceFeatures(size=self.features_size,utterance=stem_obs),weight=scale)
        #feat.merge(UtteranceFeatures(size=self.features_size,utterance=abs_stem_obs),weight=scale)
        #feat.merge(UtteranceFeatures(size=self.features_size,utterance=abs_stem_obs2),weight=scale)

        return feat

    def get_features_in_nblist(self, obs, fvc, fvcs):
        return None

    def get_features_in_confnet(self, obs, fvc, fvcs):
        return None

    def get_features(self, obs, fvc):
        """
        Generate utterance features for a specific utterance given by utt_idx.

        :param obs: the utterance being processed in multiple formats
        :param fvc: a form, value category tuple describing how the utterance should be abstracted
        :return: a set of features from the utterance
        """
        if isinstance(obs, Utterance):
            return self.get_features_in_utterance(obs, fvc)
        elif isinstance(obs, UtteranceConfusionNetwork):
            return self.get_features_in_confnet(obs, fvc)
        elif isinstance(obs, UtteranceNBList):
            return self.get_features_in_nblist(obs, fvc)
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
                self.get_abstract_das(self.das[utt_idx],self.utterance_fvc[utt_idx])

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
        for k in self.classifiers:
            if '=' in k and '0' not in k and self.classifiers[k] < min_classifier_count:
                continue

            if '="dontcare"' in k and '(="dontcare")' not in k:
                continue

            if 'null()' in k:
                continue

            new_classifiers[k] = self.classifiers[k]

        self.classifiers = new_classifiers


    def print_classifiers(self):
        print "=" * 120
        print "Classifiers detected in the training data"
        print "-" * 120
        print "Number of classifiers: ", len(self.classifiers)
        print "-" * 120

        for k in sorted(self.classifiers):
            print('%40s = %d' % (k, self.classifiers[k]))

    def gen_classifiers_data(self, verbose=False):
        # generate training data
        self.classifiers_outputs = defaultdict(list)
        self.classifiers_cls = defaultdict(list)
        self.classifiers_features = defaultdict(list)

        self.parsed_classifiers = {}
        for clser in self.classifiers:
            self.parsed_classifiers[clser] = DialogueActItem()
            self.parsed_classifiers[clser].parse(clser)

        for utt_idx in self.utterances_list:
            if verbose:
                print "-" * 120
                print unicode(self.utterances[utt_idx])
                print unicode(self.das[utt_idx])

            for clser in self.classifiers:
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
                            self.get_features(self.utterances[utt_idx], self.das_category_labels[utt_idx][i]))

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

                    self.classifiers_features[clser].append(self.get_features(self.utterances[utt_idx], (None, None, None)))

                    if verbose:
                        print "  @", clser

        for clser in self.classifiers:
            self.classifiers_outputs[clser] = np.array(self.classifiers_outputs[clser])

            if verbose:
                print clser
                print zip(self.classifiers_outputs[clser], self.classifiers_cls[clser])

    def prune_features(self, min_feature_count=5, verbose=False):

        self.classifiers_features_list = {}
        self.classifiers_features_mapping = {}

        if verbose:
            print '=' * 120
            print 'Pruning features'
            print '-' * 120

        for clser in self.classifiers:
            if verbose:
                print "Classifier: ", clser

            features_counts = defaultdict(int)
            for feat in self.classifiers_features[clser]:
                for f in feat:
                    features_counts[f] += 1

            if verbose:
                print "  Number of features: ", len(features_counts)

            remove_features = []
            for f in features_counts:
                if features_counts[f] < min_feature_count:
                    remove_features.append(f)

            if verbose:
                print "  Number of features occurring less then %d times: %d" % (min_feature_count, len(remove_features))

            remove_features = set(remove_features)
            for feat in self.classifiers_features[clser]:
                feat.prune(remove_features)

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


    def gen_classifiers_inputs(self, verbose=True):
        self.classifiers_inputs = {}

        if verbose:
            print '=' * 120
            print 'Generating input matrix'
            print '-' * 120

        for clser in self.classifiers:
            if verbose:
                print "Computing features for %s" % (clser, )

            self.classifiers_inputs[clser] = np.zeros((len(self.classifiers_outputs[clser]), len(self.classifiers_features_list[clser])))

            for i, feat in enumerate(self.classifiers_features[clser]):
                self.classifiers_inputs[clser][i] = feat.get_feature_vector(self.classifiers_features_mapping[clser])


    def train(self, inverse_regularisation=1.0, verbose=True):
        self.trained_classifiers = {}

        if verbose:
            print '=' * 120
            print 'Training'
            print '-' * 120

        for clser in sorted(self.classifiers):
            if verbose:
                print "Training classifier: ", clser

            lr = LogisticRegression('l2', C=inverse_regularisation, tol=1e-6)
            lr.fit(self.classifiers_inputs[clser], self.classifiers_outputs[clser])
            self.trained_classifiers[clser] = lr

            if verbose:
                mean_accuracy = lr.score(self.classifiers_inputs[clser], self.classifiers_outputs[clser])
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

    def parse_1_best(self, obs=dict(), ret_cl_map=False, verbose=False, *args, **kwargs):
        """
        Parse ``utterance`` and generate the best interpretation in the form of
        a dialogue act (an instance of DialogueAct).

        The result is the dialogue act confusion network.

        """
        utterance = obs.get('utt', None)
        if utterance is None:
            raise DAILRException("Need to get an utterance to parse.")
        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        if verbose:
            print '='*120
            print 'Parsing 1 best'
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
                        classifiers_features = self.get_features(utterance, (f, v, cc))
                        classifiers_inputs = np.zeros((1, len(self.classifiers_features_mapping[clser])))
                        classifiers_inputs[0] = classifiers_features.get_feature_vector(self.classifiers_features_mapping[clser])

                        #if verbose:
                        #    print classifiers_features
                        #    print self.classifiers_features_mapping[clser]

                        p = self.trained_classifiers[clser].predict_proba(classifiers_inputs)

                        if verbose:
                            print '  Probability:', p

                        dai = DialogueActItem(self.parsed_classifiers[clser].dat, self.parsed_classifiers[clser].name, v)
                        da_confnet.add(p[0][1], dai)
            else:
                # process concrete classifiers
                classifiers_features = self.get_features(utterance, (None, None, None))
                classifiers_inputs = np.zeros((1, len(self.classifiers_features_mapping[clser])))
                classifiers_inputs[0] = classifiers_features.get_feature_vector(self.classifiers_features_mapping[clser])

                #if verbose:
                #    print classifiers_features
                #    print self.classifiers_features_mapping[clser]

                p = self.trained_classifiers[clser].predict_proba(classifiers_inputs)

                if verbose:
                    print '  Probability:', p

                da_confnet.add(p[0][1], self.parsed_classifiers[clser])

        #if verbose:
        #    print "DA conf net:"
        #    print da_confnet

        #da_confnet = self.preprocessing.category_labels2values_in_confnet(da_confnet, category_labels)
        da_confnet.sort().merge()

        return da_confnet

    def parse_nblist(self, obs, *args, **kwargs):
        """
        Parses n-best list by parsing each item on the list and then merging
        the results.
        """

        utterance_list = obs['utt_nbl']
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

    def parse_confnet(self, obs, verbose=False, *args, **kwargs):
        """
        Parses the word confusion network by generating an n-best list and
        parsing this n-best list.
        """
        confnet = obs['utt_cn']
        nblist = confnet.get_utterance_nblist(n=40)
        sem = self.parse_nblist(nblist)
        return sem
