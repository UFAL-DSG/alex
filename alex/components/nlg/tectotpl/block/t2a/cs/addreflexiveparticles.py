#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddReflexiveParticles(Block):
    """
    Add reflexive particles to reflexiva tantum and reflexive passive verbs.

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
        "Add reflexive particle to a node, if applicable."
        tantum_match = re.search(r'_(s[ei])$', tnode.t_lemma)
        # reflexiva tantum
        if tantum_match:
            refl_form = tantum_match.group(1)
            afun = 'AuxT'
        # reflexive passive
        elif tnode.voice == 'reflexive_diathesis' or \
                tnode.gram_diathesis == 'deagent':
            refl_form = 'se'
            afun = 'AuxR'
        # no particle to add
        else:
            return
        # add the particle
        anode = tnode.lex_anode
        refl_node = anode.create_child()
        refl_node.form = refl_form
        refl_node.afun = afun
        refl_node.lemma = refl_form
        refl_node.morphcat_pos = 'P'
        refl_node.morphcat_subpos = '7'
        refl_node.morphcat_number = 'X'
        refl_node.morphcat_case = refl_form == 'si' and '3' or '4'
        # to be moved to Wackernagel position later
        refl_node.shift_after_node(anode)
        # add auxiliary link
        tnode.add_aux_anodes(refl_node)
