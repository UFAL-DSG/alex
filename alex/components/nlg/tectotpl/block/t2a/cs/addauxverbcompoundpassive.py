#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddAuxVerbCompoundPassive(Block):
    """
    Add compound passive auxiliary 'být'.

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
        "Add compound passive auxiliary to a node, where appropriate."
        # only apply where appropriate
        if tnode.voice != 'passive' and tnode.gram_diathesis != 'pas':
            # mark conjugated verb for future reference
            if tnode.lex_anode and tnode.lex_anode.morphcat_pos == 'V':
                tnode.set_deref_attr('wild/conjugated', tnode.lex_anode)
            return
        anode = tnode.lex_anode
        aux_node = anode.create_child()
        aux_node.shift_before_node(anode)
        # copy original categories of the lexical verb
        aux_node.morphcat = dict(anode.morphcat)
        aux_node.morphcat_voice = 'A'
        aux_node.lemma = 'být'
        aux_node.afun = 'AuxV'
        tnode.add_aux_anodes(aux_node)
        # change the categories of the lexical verb to passive
        anode.morphcat_pos = 'V'
        anode.morphcat_subpos = 's'
        anode.morphcat_negation = 'A'
        anode.morphcat_voice = 'P'
        # mark that the auxiliary is conjugated
        tnode.set_deref_attr('wild/conjugated', aux_node)
