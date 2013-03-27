#!/usr/bin/env python
# coding=utf-8
#
# A treex block
#
from __future__ import unicode_literals

import re
from alex.components.nlg.tectotpl.block.t2a.imposeagreement import ImposeAgreement

__author__ = "Ondřej Dušek"
__date__ = "2012"


class ImposeComplAgr(ImposeAgreement):
    """
    Impose agreement of adjectival verb complements with the subject.
    
    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """
    
    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        super(ImposeComplAgr, self).__init__(scenario, args)
        

    def should_agree(self, tnode):
        "Find the complement and its subject."
        if not re.match(r'^adj:(compl|[1-7])$', tnode.formeme):
            return False
        # Find finite verb
        tclhead = tnode.get_clause_root()
        if not re.match(r'^v:.*(fin|rc)$', tclhead.formeme):
            return False
        # Find subject
        aclhead = tclhead.lex_anode
        anode = tnode.lex_anode
        try:
            asubj = next(achild for achild in aclhead.get_echildren() if achild.afun == 'Sb')
        except StopIteration:
            return False
        return (anode, aclhead, asubj)
        
    
    def process_excepts(self, tnode, match_nodes):
        "Returns False; there are no special cases for this rule."
        return False
    
    def impose(self, tnode, match_nodes):
        "Impose the agreement on selected adjectival complements."
        anode, aclhead, asubj = match_nodes
        # Fill only the categories that have not been already set by someone else
        if anode.morphcat_case == '.': 
            anode.morphcat_case = asubj.morphcat_case
        if anode.morphcat_number == '.': 
            anode.morphcat_number = aclhead.morphcat_number
        if anode.morphcat_gender == '.': 
            anode.morphcat_gender = aclhead.morphcat_gender
