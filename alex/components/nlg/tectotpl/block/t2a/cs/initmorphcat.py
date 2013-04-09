#!/usr/bin/env python
# coding=utf-8
#
# Creating an a-tree from a t-tree.
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class InitMorphcat(Block):
    """
    According to t-layer grammatemes, this initializes the morphcat structure
    at the a-layer that is the basis for a later POS tag limiting in the word
    form generation.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    GENDER = {None: '.', 'anim': 'M', 'inan': 'I', 'fem': 'F',
              'neut': 'N', 'nr': '.', 'inher': '.'}
    NUMBER = {None: '.', 'sg': 'S', 'pl': 'P', 'nr': '.', 'inher': '.'}
    DEGREE = {None: '.', 'pos': '1', 'comp': '2', 'acomp': '2',
              'sup': '3', 'nr': '.'}
    PERSON = {None: '.', '1': '1', '2': '2', '3': '3', 'inher': '.'}
    NEGATION = {None: 'A', 'neg0': 'A', 'neg1': 'N'}
    VOICE = {None: '.', 'active': 'A', 'passive': 'P',
             'act': 'A', 'pas': 'P', 'deagent': 'A'}

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_tnode(self, tnode):
        "Initialize the morphcat structure in the given node"
        # obtain anode
        anode = tnode.lex_anode
        if not anode:
            return
        # rule out uninflected words
        if tnode.nodetype in ['coap', 'atom', 'dphr']:
            anode.morphcat_pos = '!'
            return
        # POS (more or less not needed)
        anode.morphcat_pos = tnode.mlayer_pos or '.'
        if tnode.formeme.startswith('v'):
            anode.morphcat_pos = 'V'
        if tnode.t_lemma == ':':
            anode.morphcat_pos = 'Z'
        # set 'simple' things
        anode.morphcat_person = self.PERSON[tnode.gram_person]
        anode.morphcat_number = self.NUMBER[tnode.gram_number]
        anode.morphcat_gender = self.GENDER[tnode.gram_gender]
        # set detailed categories for personal pronouns
        if tnode.t_lemma == '#PersPron':
            self.set_perspron_categories(tnode, anode)
        # set case
        self.set_case(tnode, anode)
        # set degree of comparison
        degree = tnode.gram_degcmp
        if re.match(r'quant|pron', tnode.gram_sempos or ''):
            degree = None
        anode.morphcat_grade = self.DEGREE[degree]
        # set negation
        if re.match(r'^[nav](?!.*(pron|quant))', tnode.gram_sempos or '') and \
                tnode.t_lemma != '#PersPron':
            anode.morphcat_negation = self.NEGATION[tnode.gram_negation]
        # set voice
        if (tnode.gram_sempos or '').startswith('v'):
            anode.morphcat_voice = self.VOICE[tnode.voice or
                                              tnode.gram_diathesis]

    def set_case(self, tnode, anode):
        """\
        Set the morphological case for an a-node according to the
        corresponding t-node's formeme, where applicable.
        """
        # take the case directly from the formeme, if possible
        case = re.search(r'(\d)', tnode.formeme)
        if case:
            anode.morphcat_case = case.group(1)
        # pro-drop pronouns are assumed to have nominative case
        # (since this is how a subject is searched for)
        elif tnode.formeme == 'drop':
            anode.morphcat_case = '1'
        # this is actually a hack for older formemes which lacked case
        # in adjectives with prepositions
        elif re.match(r'^adj:za+X$', tnode.formeme):
            anode.morphcat_case = '4'

    def set_perspron_categories(self, tnode, anode):
        """\
        Set detailed morphological categories of personal pronouns
        of various types (possessive, reflexive, personal per se)
        """
        # possessive/reflexive possessive pronouns
        if re.search(r'poss|attr', tnode.formeme):
            # reflexive possessive
            tnouns = tnode.get_eparents()
            if tnouns and tnode.coref_gram_nodes and \
                    not (tnouns[0].formeme and '1' in tnouns[0].formeme):
                anode.morphcat_person = '.'
                anode.morphcat_subpos = '8'
                return
            # other possessive
            anode.morphcat_possnumber = self.NUMBER[tnode.gram_number]
            if anode.morphcat_person == '3':
                anode.morphcat_possgender = self.GENDER[tnode.gram_gender]
            anode.morphcat_subpos = 'S'
            return
        # plain reflexive pronouns
        if tnode.is_reflexive:
            anode.morphcat_person = '.'
            if re.search(r'[^+][34]', tnode.formeme):
                # no preposition - short 'se', 'si'
                anode.morphcat_subpos = '7'
            else:
                # after preposition - long 'sebe', 'sobě'
                anode.morphcat_subpos = '6'
            return
        # personal pronouns after prepositions -- 'něho', 'něm' etc.
        if re.match(r'n:.*\+', tnode.formeme) and anode.morphcat_person == '3':
            anode.morphcat_subpos = '3'
        # personal pronoun 'ho', 'mu'
        elif re.search(r'[34]', tnode.formeme) and \
                tnode.gram_number == 'sg' and tnode.gram_gender != 'fem':
            anode.morphcat_subpos = 'H'
        # default form
        else:
            anode.morphcat_subpos = 'P'
