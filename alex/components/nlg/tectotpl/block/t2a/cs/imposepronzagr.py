#!/usr/bin/env python
# coding=utf-8
#
# A treex block
#
from __future__ import unicode_literals

import re
from treex.block.t2a.imposeagreement import ImposeAgreement

__author__ = "Ondřej Dušek"
__date__ = "2012"


class ImposePronZAgr(ImposeAgreement):
    """
    In phrases such as 'každý z ...','žádná z ...', impose agreement in gender.
    
    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """
    
    PRONOUNS = r'^(jeden|každý|žádný|oba|všechen|(ně|lec)který|(jak|kter)ýkoliv?|libovolný)$'
    
    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        super(ImposePronZAgr, self).__init__(scenario, args)
        

    def should_agree(self, tnode):
        "Find matching pronouns with 'z+2'-formeme children."
        if not re.match(self.PRONOUNS, tnode.t_lemma): return False
        try:
            return next(tchild for tchild in tnode.get_children() if tchild.formeme == 'n:z+2')
        except StopIteration:
            return False
        
    
    def process_excepts(self, tnode, match_nodes):
        "Returns False; there are no special cases for this rule."
        return False
    
    def impose(self, tnode, tchild):
        "Impose the gender agreement on selected nodes."
        anode = tnode.lex_anode
        achild = tchild.lex_anode
        anode.morphcat_gender = achild.morphcat_gender 