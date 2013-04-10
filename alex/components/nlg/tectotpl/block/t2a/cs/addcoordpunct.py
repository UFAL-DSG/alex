#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
from alex.components.nlg.tectotpl.tool.lexicon.cs import Lexicon

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddCoordPunct(Block):
    """
    Add comma to coordinated lists of 3 and more elements, as well as before
    some Czech coordination conjunctions ('ale', 'ani').

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')
        self.lexicon = Lexicon()

    def process_anode(self, anode):
        "Add coordination punctuation to the given anode, if applicable."
        if anode.afun != 'Coord':
            return
        achildren = anode.get_children(ordered=True)
        if not achildren:
            return
        # add comma before certain conjunctions
        if self.lexicon.is_coord_conj(anode.lemma) == 'Y' and \
                self.is_at_clause_boundary(anode):
            acomma = self.add_comma_node(anode)
            acomma.shift_before_node(anode)
        # add comma in lists with multiple members (before every member
        # except the first one and the last one, which is connected with
        # the conjunction)
        for aprec_member in [an for an in anode.get_children()
                             if an.is_member and an < anode][1:]:
            acomma = self.add_comma_node(anode)
            acomma.shift_before_subtree(aprec_member)

    def add_comma_node(self, anode):
        "Add a comma AuxX node under the given node."
        return anode.create_child(data={'form': ',', 'lemma': ',',
                                        'afun': 'AuxX',
                                        'morphcat': {'pos': 'Z'},
                                        'clause_number': 0})

    def is_at_clause_boundary(self, anode):
        """Return true if the given node is at a clause boundary (i.e. the
        nodes immediately before and after it belong to different clauses)."""
        prev_node = anode.get_prev_node()
        next_node = anode.get_next_node()
        return prev_node and next_node and \
                prev_node.clause_number != next_node.clause_number
