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

from collections import defaultdict

from alex.components.asr.utterance import Utterance, UtteranceHyp, UtteranceNBList, UtteranceConfusionNetwork
from alex.components.slu.exceptions import SLUException, DAILRException
from alex.components.slu.base import SLUInterface
from alex.components.slu.da import DialogueActItem, DialogueActConfusionNetwork, merge_slu_confnets
from alex.utils.config import load_as_module
from alex.utils.various import nesteddict

class SlotValueFormDatabase(object):
    """ Provides a convenient interface to a database of slot value forms tuples.

    Attributes:
          form_value_category: a list of (form, value, slot) tuples

    """

    def __init__(self, file_name):
        self.database = {}
        self.forms = []
        self.form_value_slot = []
        self.form2value2slot = nesteddict()

        if file_name:
            self.load(file_name)

    def __iter__(self):
        """Yields tuples (form, value, slot) from the database."""

        for i in self.form_value_slot:
            yield i

    def load(self, file_name):
        """
        Load the database with slots, values, and forms from a file.

        :param file_name: a file name of a the slot value form database file

        """

        db_mod = load_as_module(file_name, force=True)
        if not hasattr(db_mod, 'database'):
            raise SLUException("The slot value form database does not define the `database' object!")
        self.database = db_mod.database

        self.normalise_database()
        # Update derived data structures.
        self.gen_form_value_slot_list()
        self.gen_mapping_form2value2slot()


    def normalise_database(self):
        """Normalise database. E.g. split utterances into sequences of words.
        """
        new_db = dict()
        for name in self.database:
            new_db[name] = dict()
            for value in self.database[name]:
                new_db[name][value] = [tuple(form.split()) for form in self.database[name][value]]
        self.database = new_db


    def gen_form_value_slot_list(self):
        """
        Generates an list of form, value, slot tuples from the database. This list is ordered where the tuples
        with the longest surface forms are at the beginning of the list.

        :return: none
        """
        for slot in self.database:
            for value in self.database[slot]:
                for form in self.database[slot][value]:
                    self.form_value_slot.append((form, value, slot))

        self.form_value_slot.sort(key=lambda fvs: len(fvs[0]), reverse=True)

    def gen_mapping_form2value2slot(self):
        """
        Generates an list of form, value, slot tuples from the database . This list is ordered where the tuples
        with the longest surface forms are at the beginning of the list.

        :return: none
        """

        for slot in self.database:
            for value in self.database[slot]:
                for form in self.database[slot][value]:
                    self.form2value2slot[form][value][slot] = 1
                    self.forms.append(form)

        self.forms.sort(key=lambda f: len(f), reverse=True)


class SLUPreprocessing(object):
    """Implements preprocessing of utterances or utterances and dialogue acts.
    The main purpose is to replace all values in the database by their slot
    labels (slot names) to reduce the complexity of the input utterances.

    In addition, it implements text normalisation for SLU input, e.g. removing
    filler words such as UHM, UM etc., converting "I'm" into "I am" etc.  Some
    normalisation is hard-coded. However, it can be updated by providing
    normalisation patterns.

    """
    text_normalization_mapping = [(['erm', ], []),
                                  (['uhm', ], []),
                                  (['um', ], []),
                                  (["i'm", ], ['i', 'am']),
                                  (['(sil)', ], []),
                                  (['(%hesitation)', ], []),
                                  (['(hesitation)', ], []),
    ]

    def __init__(self, svfdb, text_normalization=None):
        """Initialises a SLUPreprocessing object with particular preprocessing
        parameters.

        :param svfdb: an iterable of (surface, value, slot) tuples describing the
                     relation between surface forms and (slot, value) pairs
        :param text_normalization:  an iterable of tuples (source, target) where
                                    ``source`` occurrences in the text should be substituted by
                                    ``target``, both `source' and `target' being specified as
                                     a sequence of words

        """
        self.svfdb = svfdb

        if text_normalization:
            self.text_normalization_mapping = text_normalization

    def normalise_utterance(self, utterance):
        """
        Normalises the utterance (the output of an ASR).

        E.g., it removes filler words such as UHM, UM, etc., converts "I'm"
        into "I am", etc.

        """
        utterance.lower()
        for mapping in self.text_normalization_mapping:
            utterance = utterance.replace(mapping[0], mapping[1])
        return utterance

    def normalise_confnet(self, confnet):
        """
        Normalises the confnet (the output of an ASR).

        E.g., it removes filler words such as UHM, UM, etc., converts "I'm"
        into "I am", etc.

        """
        confnet.lower()
        for mapping in self.text_normalization_mapping:
            confnet = confnet.replace(mapping[0], mapping[1])
        return confnet

    def normalise(self, utt_hyp):
        if isinstance(utt_hyp, Utterance):
            return self.normalise_utterance(utt_hyp)
        elif isinstance(utt_hyp, UtteranceConfusionNetwork):
            return self.normalise_confnet(utt_hyp)
        elif isinstance(utt_hyp, UtteranceNBList):
            for utt_idx, hyp in enumerate(utt_hyp):
                utt_hyp[utt_idx][1] = self.text_normalisation(hyp[1])
        else:
            raise SLUException("Unsupported utterance hypothesis.")


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

    def __init__(self, svfdb, preprocessing, features_size=4, *args, **kwargs):
        self.features_size = features_size
        self.preprocessing = preprocessing
        self.svfdb = svfdb

    def abstract_utterance(self, utterance):
        """
        Return a list of possible abstractions of the utterance.

        :param utterance: an Utterance instance
        :return: a list of abstracted utterance, form, value, slot tuples
        """

        abs_utts = []

        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end >  start:
                f = tuple(utterance[start:end])
                #print start, end
                #print f

                if f in self.svfdb.form2value2slot:
                    for v in self.svfdb.form2value2slot[f]:
                        for s in self.svfdb.form2value2slot[f][v]:
                            u = copy.deepcopy(utterance)
                            u = u.replace2(start,end,'SLOT_'+s.upper())

                            abs_utts.append((u,f,v,s))

                    #print f
                    break
                end -= 1
            start += 1
        return abs_utts

    def get_fvs_in_utterance(self, utterance):
        """
        Return a list of all form, value, slot tuples in the utterance.
        This is useful to find/guess what slot level classifiers will be necessary to instantiate.

        :param utterance: an Utterance instance
        :return: a list of forms, values, and slots found in the input sentence
        """

        fvss = set()

        start = 0
        while start < len(utterance):
            end = len(utterance)
            while end >  start:
                f = tuple(utterance[start:end])

                # this looks for an exact surface form in the SVFDB
                # however, we could also search for those withing a some distance from the exact surface form,
                # for example using a string edit distance
                if f in self.svfdb.form2value2slot:
                    for v in self.svfdb.form2value2slot[f]:
                        for s in self.svfdb.form2value2slot[f][v]:
                            fvss.add((f,v,s))

                    break
                end -= 1
            start += 1

        return fvss

    def get_abstract_das(self, da, fvss):
        new_da = copy.deepcopy(da)
        c_fvss = copy.deepcopy(fvss)
        
        cli = 0
        dai_cl_2_v_f = []
        for dai in new_da:
            
            for fvs in c_fvss:
                f, v, s = fvs
                if dai.value == v:
                    dai.value = 'CL_'+s.upper()
                    
                    c_fvss.remove(fvs)
                    dai_cl_2_v_f.append((v,f))
                    break
            else:
                dai_cl_2_v_f.append((None,None))
            
        print new_da, dai_cl_2_v_f
        
        return new_da, dai_cl_2_v_f

    def get_fvs_in_nblist(self, nblist):
        """
        Return a list of all form, value, slot tuples in the nblist.

        :param nblist: an UtteranceNBList instance
        :return:
        """
        pass

    def get_fvs_in_confnet(self, confnet):
        """
        Return a list of all form, value, slot tuples in the confusion network.

        :param nblist: an UtteranceConfusionNetwork instance
        :return:
        """
        pass

    def get_fvs(self, obs):
        if isinstance(obs, Utterance):
            return self.get_fvs_in_utterance(obs)
        elif isinstance(obs, UtteranceConfusionNetwork):
            return self.get_fvs_in_confnet(obs)
        elif isinstance(obs, UtteranceNBList):
            return self.get_fvs_in_nblist(obs)
        else:
            raise DAILRException("Unsupported observations.")

    def extract_classifiers(self, das, utterances, verbose=False):
        # process the training data
        self.utterances = utterances
        self.das = das

        self.utterances_list = self.utterances.keys()

        self.utterance_fvs = {}
        self.das_abstracted = {}
        self.das_category_labels = {}
        for utt_idx in self.utterances_list:
            self.utterances[utt_idx] = self.preprocessing.normalise(self.utterances[utt_idx])
            self.utterance_fvs[utt_idx] = self.get_fvs(self.utterances[utt_idx])
            self.das_abstracted[utt_idx], self.das_category_labels[utt_idx] = self.get_abstract_das(self.das[utt_idx],self.utterance_fvs[utt_idx])

        # get the classifiers
        self.classifiers = defaultdict(int)
        self.classifiers_abstracted = defaultdict(int)

        for k in self.utterances_list:
            for dai in self.das_abstracted[k].dais:
                self.classifiers[unicode(dai)] += 1

#            for dai in self.das_abstracted[k].dais:
 #               self.classifiers_abstracted[unicode(dai)] += 1

                if verbose:
                    if dai.value and 'CL_' not in dai.value:
                        print '=' * 120
                        print 'Un-abstracted slot value'
                        print '-' * 120
                        print unicode(self.utterances[k])
                        print unicode(self.utterance_fvs[k])
                        print unicode(self.das[k])
                        print unicode(self.das_abstracted[k])


    def prune_abstracted_classifiers(self, min_classifier_count=5):
        new_classifiers = {}
        for k in self.classifiers_abstracted:
            if '=' in k and '0' not in k and self.classifiers_abstracted[k] < min_classifier_count:
                continue

            if '="dontcare"' in k and '(="dontcare")' not in k:
                continue

            new_classifiers[k] = self.classifiers_abstracted[k]

        self.classifiers_abstracted = new_classifiers


    def print_classifiers(self):
        print "="*120
        print "Classifiers detected in the training data"
        print "-"*120
        print "Number of classifiers: ", len(self.classifiers)
        print "-"*120

        for k in sorted(self.classifiers):
          print('%40s = %d' % (k, self.classifiers[k]))

        print "-"*120
        print "Number of abstracted classifiers: ", len(self.classifiers_abstracted)
        print "-"*120

        for k in sorted(self.classifiers_abstracted):
          print('%40s = %d' % (k, self.classifiers_abstracted[k]))

    def gen_classifiers_outputs(self):
        # generate training data
        self.classifiers_outputs = defaultdict(list)
        self.classifiers_cls = defaultdict(list)

        for utt_idx in self.utterances_list:
            print "-"*120
            print unicode(self.utterances[utt_idx])
            
            for c in self.classifiers:
                for i, dai in enumerate(self.das_abstracted[utt_idx]):
                    if c == dai:
                        self.classifiers_outputs[c].append(1.0)
                        self.classifiers_cls[c].append(self.das_category_labels[utt_idx][i])
                        break
                else:
                    self.classifiers_outputs[c].append(0.0)
                    self.classifiers_cls[c].append((None,None))
                    
                print c,
                print self.classifiers_outputs[c][-1], 
                print self.classifiers_cls[c][-1]

        for c in self.classifiers:
            self.classifiers_outputs[c] = np.array(self.classifiers_outputs[c])

    def get_utterance_features(self):
        pass

    def extract_features(self, das, utterances, verbose=False):

        # generate utterance features.
        self.utterance_features = {}
        #for utt_idx in self.utterances_list:
        #    self.utterance_features[utt_idx] = UtteranceFeatures('ngram', self.features_size, self.utterances[utt_idx])
        #    if isinstance(utt_hyp, Utterance):
        #        self.utterance_features[utt_idx] = UtteranceFeatures('ngram', self.features_size, self.utterances[utt_idx])
        #    elif isinstance(utt_hyp, UtteranceConfusionNetwork):
        #        self.utterance_features[utt_idx] = UtteranceConfusionNetworkFeatures('ngram', self.features_size, self.utterances[utt_idx])
        #    else:
        #        assert isinstance(utt_hyp, UtteranceNBList)
        #        self.utterance_features[utt_idx] = UtteranceNBListFeatures('ngram', self.features_size, self.utterances[utt_idx])

    def prune_features(self, min_feature_count=5, verbose=False):
        pass


    def gen_input_matrix(self):
        pass

    def train(self, verbose=True):
        pass

    def save_model(self, file_name, gzip=None):
        data = [self.features_list, self.features_mapping, self.trained_classifiers, self.features_size]

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
            (self.features_list, self.features_mapping, self.trained_classifiers, self.features_size) = pickle.load(model_file)

    def get_size(self):
        return len(self.features_list)

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
            print utterance

        if self.preprocessing:
            utterance = self.preprocessing.normalise_text(utterance)
            utterance, category_labels = self.preprocessing.values2category_labels_in_utterance(utterance)

        if verbose:
            print utterance
            print category_labels

        # Generate utterance features.
        utterance_features = UtteranceFeatures('ngram', self.features_size, utterance)

        if verbose:
            print utterance_features

        kernel_vector = np.zeros((1, len(self.features_mapping)))
        kernel_vector[0] = utterance_features.get_feature_vector(self.features_mapping)

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