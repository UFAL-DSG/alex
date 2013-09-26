#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

from collections import defaultdict

import alex.components.slu.da as da

from alex.components.asr.utterance import Utterance
from alex.components.slu.exceptions import SLUException
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
        else:
            assert isinstance(utt_hyp, UtteranceNBList)
            for utt_idx, hyp in enumerate(utt_hyp):
                utt_hyp[utt_idx][1] = self.text_normalisation(hyp[1])



    def abstract_utterance(self, utterance):
        """
        Return a list of possible abstractions of the utterance.

        :param utterance: an Utterance instance
        :return:
        """

        abs_utts = []

        for start in range(0,len(utterance)):
            for end in range(start+1,len(utterance)+1):
                f = tuple(utterance[start:end])

                if f in self.svfdb.form2value2slot:
                    for v in self.svfdb.form2value2slot[f]:
                        for s in self.svfdb.form2value2slot[f][v]:
                            u = copy.deepcopy(utterance)
                            u = u.replace2(start,end,'SLOT_'+s.upper())

                            abs_utts.append((u,f,v,s))

        return abs_utts

    def values2slot_labels_in_utterance(self, utterance):
        """ Replaces all strings matching values in the database by its slot names. Since multiple slots can have
        the same values, the algorithm produces multiple outputs.

        Returns a list of utterances with replaced database values. And it provides a dictionary with mapping
        between slot labels and the original string.

        """

        utterance = copy.deepcopy(utterance)

        catgeory_label_counter = defaultdict(int)
        slot_labels = {}

        for s, value, name in self.svfdb:
            if s in utterance:
                slot_label = name.upper() + '-' + str(catgeory_label_counter[name.upper()])
                catgeory_label_counter[name.upper()] += 1

                slot_labels[slot_label] = (value, s)
                utterance.replace(s, [slot_label, ])

                break

        return utterance, slot_labels

    def values2slot_labels_in_da(self, utterance, da):
        """ Replaces all strings matching values in the database by its slot names. Since multiple slots can have
        the same values, the algorithm can produce multiple outputs.

        Returns a list of utterances with replaced database values. And it provides a dictionary with mapping
        between slot labels and the original string.

        """

        da = copy.deepcopy(da)
        utterance = copy.deepcopy(utterance)

        utterance, slot_labels = self.values2slot_labels_in_utterance(utterance)

        for cl in slot_labels:
            for dai in da:
                if dai.value == slot_labels[cl][0]:
                    dai.value = cl
                    break

        return utterance, da, slot_labels

    def slot_labels2values_in_utterance(self, utterance, slot_labels):
        """Reverts the result of the values2slot_labels_in_utterance(...) function.

        Returns the original utterance.
        """

        utterance = copy.deepcopy(utterance)

        for cl in slot_labels:
            utterance.replace([cl, ], slot_labels[cl][1])

        return utterance

    def slot_labels2values_in_da(self, da, slot_labels):
        """Reverts the result of the values2slot_labels_in_da(...) function.

        Returns the original dialogue act.
        """
        da = copy.deepcopy(da)
        for dai in da.dais:
            if dai.value in slot_labels:
                dai.value = slot_labels[dai.value][0]

        return da
