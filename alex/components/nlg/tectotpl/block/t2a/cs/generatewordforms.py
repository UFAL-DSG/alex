#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
from treex.core.resource import get_data
from treex.tool.ml.model import Model
from treex.core.util import first
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class GenerateWordForms(Block):
    """
    Inflect word forms according to filled-in tags.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    BACK_REGEX = re.compile(r'^>([0-9]+)(.*)$')

    def __init__(self, scenario, args):
        """\
        Constructor, just checking the argument values.
        """
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')
        # load the model from a pickle
        self.model = Model.load_from_file(get_data(args['model']))

    def process_atree(self, aroot):
        """\
        Inflect word forms in the given a-tree.
        """
        anodes = aroot.get_descendants(ordered=True)
        # set hard form = lemma for non-inflected words
        for anode in [anode for anode in anodes
                      if anode.morphcat_pos in ['Z', 'J', 'R', '!']]:
            anode.form = anode.lemma
        # inflect the rest
        to_process = [anode for anode in anodes
                      if anode.morphcat_pos not in ['Z', 'J', 'R', '!']]
        instances = [self.__get_features(anode) for anode in to_process]
        inflections = self.model.classify(instances)
        for anode, inflection in zip(to_process, inflections):
            self.__inflect(anode, inflection)

    def __get_features(self, anode):
        """\
        Retrieve all the features needed for morphological inflection
        and store them as a dictionary.
        """
        # add lemma and morphological information
        feats = {'Lemma': anode.lemma,
                 'Tag_POS': anode.morphcat_pos,
                 'Tag_SubPOS': anode.morphcat_subpos,
                 'Tag_Gen': anode.morphcat_gender,
                 'Tag_Num': anode.morphcat_number,
                 'Tag_Cas': anode.morphcat_case,
                 'Tag_PGe': anode.morphcat_possgender,
                 'Tag_PNu': anode.morphcat_possnumber,
                 'Tag_Per': anode.morphcat_person,
                 'Tag_Ten': anode.morphcat_tense,
                 'Tag_Gra': anode.morphcat_grade,
                 'Tag_Neg': anode.morphcat_negation,
                 'Tag_Voi': anode.morphcat_voice}
        # concatenated features
        cas = anode.morphcat_case or '?'
        num = anode.morphcat_number or '?'
        gen = anode.morphcat_gender or '?'
        feats['Tag_Cas-Num-Gen'] = cas + num + gen
        feats['Tag_Num-Gen'] = num + gen
        feats['Tag_Cas-Gen'] = cas + gen
        feats['Tag_Cas-Num'] = cas + num
        # add suffixes of length 1 - 8 (inclusive)
        for suff_len in xrange(1, 9):
            feats['LemmaSuff_' + str(suff_len)] = anode.lemma[-suff_len:]
        return feats

    def __inflect(self, anode, inflection):
        """\
        Set the anode's form according to the given inflection pattern.

        Supports front, back and mid changes (front changes currently
        unsupported by the model, there must be a different model to do
        them).
        """
        # start from lemma
        form = anode.lemma
        # replace irregular
        if inflection.startswith('*'):
            form = inflection[1:]
        # if there are changes, perform them
        elif inflection != '':
            # find out the front, mid, back changes
            diffs = inflection.split(",")
            front = first(lambda x: x.startswith('<'), diffs)
            back = first(lambda x: x.startswith('>'), diffs)
            mid = first(lambda x: '-' in x, diffs)
            # perform the changes
            add_back = ''
            # chop off the things from the back
            if back is not None:
                chop, add_back = self.BACK_REGEX.match(back).groups()
                chop = int(chop)
                if chop != 0:
                    form = form[0:-chop]
            # change mid vowel
            if mid is not None:
                orig, changed = mid.split('-')
                if len(orig) > 0:
                    pos = form.lower().rfind(orig, 0, -1)
                else:
                    pos = len(form) - 1
                if pos >= -1:
                    form = form[0:pos] + changed + form[pos + len(orig):]
            # add things to beginning and end
            if front is not None:
                form = front[1:] + form
            form = form + add_back
        # set the resulting form to the anode
        anode.form = form
