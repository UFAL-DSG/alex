#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re
from alex.components.nlg.tectotpl.tool.lexicon.cs import inflect_conditional

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddAuxVerbConditional(Block):
    """
    Add conditional auxiliary 'by'/'bych'.

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
        "Add conditional auxiliary to a node, where appropriate."
        # check if we have to add a conditional auxiliary, end if not
        if tnode.gram_verbmod != 'cdn' or re.search(r'(aby|kdyby)',
                                                    tnode.formeme):
            return
        aconj = tnode.get_deref_attr('wild/conjugated')
        # create the new node
        if aconj.afun == 'AuxV':  # auxiliary conjugated -> make it a sibling
            acdn = aconj.parent.create_child()
        else:  # normal verb conjugated -> make it a child
            acdn = aconj.create_child()
        acdn.shift_before_node(aconj)
        acdn.lemma = 'být'
        acdn.afun = 'AuxV'
        acdn.morphcat_pos = 'V'
        acdn.morphcat_subpos = 'c'
        acdn.form = inflect_conditional('by', aconj.morphcat_number,
                                        aconj.morphcat_person)
        # set tense of the original to past
        aconj.morphcat_subpos = 'p'
        # fix links
        tnode.add_aux_anodes(acdn)
