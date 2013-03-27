#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re
from alex.components.nlg.tectotpl.tool.lexicon.cs import get_possessive_adj_for

__author__ = "Ondřej Dušek"
__date__ = "2012"


class GeneratePossessiveAdjectives(Block):
    """\
    According to formemes, this changes the lemma of the surface possessive
    adjectives from the original (deep) lemma which was identical to the noun
    from which the adjective is derived, e.g. changes the a-node lemma from
    'Čapek' to 'Čapkův' if the corresponding t-node has the 'adj:poss' formeme.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        """\
        Constructor, just checking the argument values.
        """
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_tnode(self, tnode):
        """\
        Check a t-node if its lexical a-node should be changed;
        if yes, update its lemma.
        """
        # skip all nodes to which this does NOT apply
        if not re.match(r'^(n|adj):poss$', tnode.formeme) or \
                tnode.mlayer_pos == 'P' or tnode.t_lemma == '#PersPron':
            return
        anode = tnode.lex_anode
        poss_adj_lemma = get_possessive_adj_for(anode.lemma)
        # the corresponding possessive adjective exists, we can use it
        if poss_adj_lemma:
            anode.lemma = poss_adj_lemma
            anode.morphcat_pos = 'A'
            anode.morphcat_subpos = '.'
            anode.morphcat_gender = '.'  # this will be obtained via agreement
            anode.morphcat_number = '.'
        # if the possessive adjective does not exist, we resort to using
        # the noun in genitive
        else:
            tnode.formeme = 'n:2'
            anode.morphcat_case = '2'
