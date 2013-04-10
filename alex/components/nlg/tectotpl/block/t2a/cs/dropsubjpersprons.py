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


class DropSubjPersProns(Block):
    """
    Remove the Czech pro-drop subject personal pronouns (or demonstrative "to") from the a-tree.
    
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
        "Check if the a-node corresponding to the given t-node should be dropped, and do so where appropriate."
        # skip nodes to which this should not apply
        if not re.search(r'(:1|drop)$', tnode.formeme) or tnode.is_member:
            return
        # special case: drop "to" under other verbs than "být" or "znamenat"
        if tnode.t_lemma == 'ten' and not tnode.parent.t_lemma in ['být', 'znamenat']:
            self.drop_anode(tnode)
            return
        # skip everything except personal pronouns
        if tnode.t_lemma != '#PersPron':
            return
        # special case: "On byl muž, který" -> "Byl to muž, který .."
        if tnode.parent.t_lemma == 'být':
            # find the nominal predicate
            tpnom = first(lambda n: n.formeme.endswith(':1'), tnode.parent.get_children(following_only=True)) 
            # if found, detect relative clause; if detected, proceed with the transformation
            if tpnom and first(lambda n: n.formeme == 'v:rc', tpnom.get_children()):
                anode = tnode.lex_anode
                anode.lemma = 'ten'
                anode.morphcat_gender = 'N'
                anode.morphcat_subpos = 'D'
                anode.morphcat_person = '-'
                anode.shift_after_node(anode.parent)
                return
        # otherwise just drop the personal pronoun
        self.drop_anode(tnode)
        
    def drop_anode(self, tnode):
        "Remove the lexical a-node corresponding to the given t-node"
        anode = tnode.lex_anode
        if not anode:
            log_warn("Can't find a-node to be dropped:" + tnode.id)
            return
        # this should not happen, but just to be sure - rehang children
        for achild in anode.get_children():
            achild.parent = anode.parent
        # remove the node itself
        anode.remove()
        