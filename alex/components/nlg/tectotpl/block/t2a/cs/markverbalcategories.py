#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class MarkVerbalCategories(Block):
    """
    Finishes marking synthetic verbal categories: tense, finiteness, mood.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_tnode(self, tnode):
        "Marks verbal categories for a t-node."
        # work on verbal nodes only
        anode = tnode.get_deref_attr('wild/conjugated')
        if not anode:
            return
        if tnode.formeme.endswith('inf'):
            if not anode:
                print tnode.id
            self.resolve_infinitive(anode)
        elif tnode.sentmod == 'imper':
            self.resolve_imperative(tnode.lex_anode)
        elif anode.morphcat_subpos in [None, '.'] or \
                anode.morphcat_tense in [None, '.']:
            self.mark_subpos_tense(tnode, anode)

    def resolve_infinitive(self, anode):
        "Mark an infinitive a-node correctly."
        anode.morphcat_subpos = 'f'
        anode.morphcat_voice = '-'
        anode.morphcat_tense = '-'
        anode.morphcat_gender = '-'
        anode.morphcat_number = '-'
        anode.morphcat_person = '-'
        anode.morphcat_voice = '-'
        return

    def resolve_imperative(self, anode):
        "Mark an imperative a-node."
        anode.morphcat_subpos = 'i'
        anode.morphcat_tense = '-'
        anode.morphcat_voice = '-'
        anode.morphcat_person = '2'
        # (hack for incorrect generation)
        if anode.lemma == 'být':
            anode.form = 'buďte'
            anode.morphcat_pos = '!'

    def mark_subpos_tense(self, tnode, anode):
        """\
        Marks the Sub-POS and tense parts of the morphcat structure in plain
        verbal a-nodes.
        """
        # past tense, conditionals
        if tnode.gram_tense == 'ant' or tnode.gram_verbmod == 'cdn' or \
                re.search(r'(aby|kdyby)', tnode.formeme):
            anode.morphcat_subpos = 'p'
        # synthetic future
        elif tnode.gram_tense == 'post' and (tnode.gram_aspect == 'proc'
                                              or tnode.voice == 'passive' or
                                              tnode.gram_diathesis == 'pas'):
            anode.morphcat_subpos = 'B'
            anode.morphcat_tense = 'F'
        # default to present tense
        else:
            anode.morphcat_subpos = 'B'
            anode.morphcat_tense = 'P'
