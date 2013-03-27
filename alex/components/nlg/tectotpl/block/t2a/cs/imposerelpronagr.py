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


class ImposeRelPronAgr(ImposeAgreement):
    """
    Impose gender and number agreement of relative pronouns with their antecedent.
    
    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """
    
 
    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        super(ImposeRelPronAgr, self).__init__(scenario, args)
        

    def should_agree(self, tnode):
        "Find relative pronouns with a valid antecedent."
        if tnode.gram_indeftype != 'relat': return False
        antec = tnode.get_deref_attr('coref_gram.rf')
        return antec and antec[0] or False
    
    def process_excepts(self, tnode, match_nodes):
        "Returns False; there are no special cases for this rule."
        return False
    
    def impose(self, tnode, tantec):
        "Impose the gender agreement on selected nodes."
        anode = tnode.lex_anode
        aantec = tantec.lex_anode
        # possessive relative pronouns
        if re.search(r'(poss|attr)$', tnode.formeme):
            anode.morphcat_possgender = aantec.morphcat_gender
            anode.morphcat_possnumber = aantec.morphcat_number
        # plain relative pronouns
        else:
            anode.morphcat_gender = aantec.morphcat_gender
            anode.morphcat_number = aantec.morphcat_number
            