#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re
from alex.components.nlg.tectotpl.core.util import first
from alex.components.nlg.tectotpl.core.log import log_warn

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddAuxWords(Block):
    """
    Add auxiliary a-nodes according to formemes. 
    
    This is a base class for all steps adding auxiliary nodes. 
    
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
        "Add auxiliary words to the a-layer for a t-node."
        # obtain the surface forms of aux nodes, and quit if there are none
        aux_word_forms = self.get_aux_forms(tnode)
        anode = self.get_anode(tnode)
        if not aux_word_forms or not anode: return
        # create new nodes
        aux_nodes = [self.new_aux_node(anode, prep) for prep in reversed(aux_word_forms)]
        aux_nodes.reverse()
        # rehang the last aux. node as the parent of the current node and remaining aux. nodes
        aux_nodes[-1].parent = anode.parent
        anode.parent = aux_nodes[-1]
        if len(aux_nodes) > 1:
            for prep_node in aux_nodes[:-1]: prep_node.parent = aux_nodes[-1]
        # move the is_member attribute
        aux_nodes[-1].is_member = anode.is_member
        anode.is_member = None
        # add auxiliary a-node links
        tnode.add_aux_anodes(aux_nodes)
        # apply content-specific post-processing (inflection, reordering etc.) 
        self.postprocess(tnode, anode, aux_nodes)
    
    def get_aux_forms(self, tnode):
        "This should return a list of new forms for the auxiliaries, or None if none should be added"
        raise NotImplementedError        
    
    def new_aux_node(self, aparent, form):
        "Create an auxiliary node with the given surface form and parent."
        raise NotImplementedError
    
    def postprocess(self, tnode, anode, aux_nodes):
        "Apply content-specific post-processing to the newly created auxiliary a-nodes (to be overridden if needed)."
        pass
    
    def get_anode(self, tnode):
        "Return the a-node corresponding to the given t-node. Defaults to lexical a-node."
        return tnode.lex_anode
            
        
        