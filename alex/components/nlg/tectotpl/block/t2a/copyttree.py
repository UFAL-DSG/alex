#!/usr/bin/env python
# coding=utf-8
#
# Creating an a-tree from a t-tree.
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.log import log_warn
from treex.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class CopyTTree(Block):
    """
    This block creates an a-tree based on a t-tree in the same zone.

    Arguments:
        language: the language of the target zone
        selector: the selector of the target zone
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_zone(self, zone):
        "Starting tree copy"
        ttree = zone.ttree
        atree = zone.create_atree()
        self.copy_subtree(ttree, atree)

    def copy_subtree(self, troot, aroot):
        """\
        Deep-copy a subtree, creating nodes with the same attributes,
        but different IDs.
        """
        # assume the roots have been copied, just go through children
        for tnode in troot.get_children(ordered=1):
            # copy lemma, delete reflexive particles in verbs
            lemma = tnode.t_lemma or ''
            lemma = re.sub(r'_s[ei]$', '', lemma)
            # skip #Cor nodes
            if lemma != '#Cor':
                # create the new node
                anode = aroot.create_child()
                tnode.lex_anode = anode
                # set lemma and ord
                re.sub(r'_s[ie]$', '', lemma)
                anode.lemma = lemma
                anode.ord = tnode.ord
                # set coap afun, if needed
                if tnode.is_coap_root():
                    anode.afun = tnode.functor == 'APPS' and 'Apos' or 'Coord'
                anode.is_member = tnode.is_member
                anode.set_attr('wild/is_parenthesis', tnode.is_parenthesis)
                self.copy_subtree(tnode, anode)
            else:
                if tnode.get_children():
                    log_warn('#Cor node is not a leaf:' + tnode.id)
                self.copy_subtree(tnode, aroot)
