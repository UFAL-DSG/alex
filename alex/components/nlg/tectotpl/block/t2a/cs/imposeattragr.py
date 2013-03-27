#!/usr/bin/env python
# coding=utf-8
#
# A treex block
#
from __future__ import unicode_literals

import re
from treex.block.t2a.imposeagreement import ImposeAgreement
from treex.tool.lexicon.cs import number_for

__author__ = "Ondřej Dušek"
__date__ = "2012"


class ImposeAttrAgr(ImposeAgreement):
    """
    Impose case, gender and number agreement of attributes with their
    governing nouns.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        super(ImposeAttrAgr, self).__init__(scenario, args)

    def should_agree(self, tnode):
        """\
        Find adjectives with a noun parent. Returns the a-layer nodes for the
        adjective and its parent, or False
        """
        if not re.search(r'(attr|poss)', tnode.formeme):
            return False
        anode = tnode.lex_anode
        if not anode:
            return False
        try:
            tnoun = tnode.get_eparents()[0]
            anoun = tnoun.lex_anode
            if anoun.is_root:
                return False
            return (anode, anoun)
        except:
            return False

    def process_excepts(self, tnode, match_nodes):
        "Handle special cases for this rule: nic/něco, numerals."
        anode, anoun = match_nodes
        if anoun.lemma in ['nic', 'něco']:
            # Case agreement, except in nominative and accusative,
            # which require genitive
            anode.morphcat_case = anoun.morphcat_case not in ['1', '4'] and \
                    anoun.morphcat_case or '2'
            # Forced neutrum singular
            anode.morphcat_number = 'S'
            anode.morphcat_gender = 'N'
            return True
        numeral = number_for(anoun.lemma)
        if numeral is not None and numeral > 1:
            # Force plural in numerals
            anode.morphcat_case = anoun.morphcat_case
            anode.morphcat_gender = anoun.morphcat_gender
            anode.morphcat_number = 'P'
            return True
        return False

    def impose(self, tnode, match_nodes):
        "Impose case, gender and number agreement on attributes."
        anode, anoun = match_nodes
        # Case agreement should take place every time
        anode.morphcat_case = anoun.morphcat_case
        # Gender and number: not for nouns
        if tnode.formeme != 'n:attr' or tnode.mlayer_pos != 'N':
            anode.morphcat_number = anoun.morphcat_number
            anode.morphcat_gender = anoun.morphcat_gender
