#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddAuxVerbModal(Block):
    """
    Add modal verbs.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    DEONTMOD_2_MODAL = {'poss': 'moci', 'vol': 'chtít', 'deb': 'muset',
                        'hrt': 'mít', 'fac': 'moci', 'perm': 'moci'}

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_tnode(self, tnode):
        "Add modal auxiliary to a node, where appropriate."
        # check if we have a modal to add, end if not
        modal = self.DEONTMOD_2_MODAL.get(tnode.gram_deontmod)
        if not modal:
            return
        alex = tnode.lex_anode
        aconjug = tnode.get_deref_attr('wild/conjugated')
        # create a new node and move the lexical verb to it
        anew = alex.create_child()
        anew.shift_after_node(aconjug)
        if aconjug == alex:
            aconjug = anew
        anew.morphcat = alex.morphcat
        anew.afun = 'Obj'
        anew.lemma = alex.lemma
        # take the conjugation for the new modal node,
        # set the previously conjugated node to infinitive
        alex.morphcat = dict(aconjug.morphcat)
        aconjug.morphcat_subpos = 'f'
        aconjug.morphcat_negation = 'A'  # negation is simplified
        # set modal node lemma
        alex.lemma = modal
        # handle links
        tnode.set_deref_attr('wild/conjugated', alex)
        tnode.lex_anode = anew
        tnode.add_aux_anodes(alex)
