#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
import re
from treex.block.t2a.addauxwords import AddAuxWords

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddPrepositions(AddAuxWords):
    """
    Add prepositional a-nodes according to formemes.
    
    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """
    
    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        super(AddPrepositions, self).__init__(scenario, args)
        if self.language is None: 
            raise LoadingException('Language must be defined!')
        

    def get_aux_forms(self, tnode):
        "Find prepositional nodes to be created."
        match = re.match(r'^(?:n|adj):(.+)[+]', tnode.formeme)
        if not match: return None
        # obtain the surface forms of the prepositions
        return match.group(1).split('_')

    def postprocess(self, tnode, anode, aux_nodes):        
        "Move rhematizers in front of the newly created PPs."
        tchildren = tnode.get_children(preceding_only=True)
        if tnode.formeme.startswith('n:') and tchildren and tchildren[0].lex_anode \
                and (tchildren[0].functor == 'RHEM' or tchildren[0].formeme.startswith('adv')):
            tchildren[0].lex_anode.shift_before_node(aux_nodes[0])
            
    def new_aux_node(self, anode, form):
        "Create a prepositional node with the given preposition form and parent."
        new_node = anode.create_child()
        new_node.form = form
        new_node.afun = 'AuxP'
        new_node.lemma = form
        new_node.morphcat_pos = 'R'
        new_node.shift_before_subtree(anode)
        return new_node
        
        
