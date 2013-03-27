#!/usr/bin/env python
# coding=utf-8
#
# A treex block
#
from __future__ import unicode_literals

import re
from alex.components.nlg.tectotpl.block.t2a.imposeagreement import ImposeAgreement
from alex.components.nlg.tectotpl.tool.lexicon.cs import is_incongruent_numeral
from alex.components.nlg.tectotpl.core.util import first

__author__ = "Ondřej Dušek"
__date__ = "2012"


class ImposeSubjPredAgr(ImposeAgreement):
    """
    Impose gender and number agreement of relative pronouns with their antecedent.
    
    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """
    
 
    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        super(ImposeSubjPredAgr, self).__init__(scenario, args)
        

    def should_agree(self, tnode):
        "Find finite verbs, with/without a subject."
        # avoid everything except finite verbs
        if not re.match(r'v.+(fin|rc)$', tnode.formeme): return False
        anode = tnode.lex_anode
        asubj = first(lambda achild: achild.afun == 'Sb', anode.get_echildren())
        return (anode, asubj)
              
    
    def process_excepts(self, tnode, match_nodes):
        "Returns False; there are no special cases for this rule."
        anode, asubj = match_nodes
        # subjectless verbs, reflexive passive and incongruent numerals: 3.ps. sg. neut.
        if (asubj is None and
                (re.match(r'^((po|z|za)?dařit|(za)?líbit)$', anode.lemma)
                 or (tnode.gram_diathesis or tnode.voice) in ['reflexive_diathesis', 'deagent'])) \
                 or (asubj and is_incongruent_numeral(asubj.lemma)):
            anode.morphcat_gender = 'N'
            anode.morphcat_number = 'S'
            anode.morphcat_person = '3'
            return True
        # This will skip all verbs without subject
        if asubj is None:
            return True        
        # Indefinite pronoun subjects
        if re.match(r'^((ně|ni|)kdo|kdokoliv?)$', asubj.lemma):
            anode.morphcat_gender = 'M'
            anode.morphcat_number = asubj.morphcat_number or 'S' #default to 'sg'
            anode.morphcat_person = '3'
            return True  
        return False
    
    def impose(self, tnode, match_nodes):
        "Impose the subject-predicate agreement on regular nodes."
        anode, asubj = match_nodes
        # Copy the categories from the subject to the predicate
        anode.morphcat_gender = asubj.morphcat_gender
        anode.morphcat_person = asubj.morphcat_person in ['1', '2', '3'] and asubj.morphcat_person or '3'
        anode.morphcat_number = asubj.morphcat_number
        # Correct for coordinated subjects
        if asubj.is_member and asubj.parent.lemma != 'nebo':
            asubj.morphcat_number = 'P'

            
