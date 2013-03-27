#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
from treex.tool.lexicon.cs import has_synthetic_future

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddAuxVerbCompoundFuture(Block):
    """
    Add compound future auxiliary 'bude'.

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
        "Add compound future auxiliary to a node, where appropriate."
        # only future tense + processual aspect or modals
        if tnode.gram_tense != 'post' or (tnode.gram_aspect != 'proc' and
                                          tnode.gram_deontmod == 'decl'):
            return
        # skip synthetic future verbs (this also rules out passives)
        aconj = tnode.get_deref_attr('wild/conjugated')
        if has_synthetic_future(aconj.lemma):
            return
        # create the new auxiliary node
        anew_aux = aconj.create_child()
        anew_aux.shift_before_node(aconj)
        anew_aux.afun = 'AuxV'
        anew_aux.lemma = 'být'
        # move conjugation
        anew_aux.morphcat = aconj.morphcat
        aconj.morphcat = {'pos': 'V', 'subpos': 'f'}
        anew_aux.morphcat_gender = '-'
        anew_aux.morphcat_tense = 'F'
        # handle links
        tnode.set_deref_attr('wild/conjugated', anew_aux)
        tnode.add_aux_anodes(anew_aux)
