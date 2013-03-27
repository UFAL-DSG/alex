#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddParentheses(Block):
    """
    Add '(' / ')' nodes to nodes which have the wild/is_parenthesis
    attribute set.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_anode(self, anode):
        "Add parentheses to an a-node, where appropriate."
        if not anode.get_attr('wild/is_parenthesis'):
            return
        # find out clause number (same as the original node,
        # or between clauses = 0)
        clause_num = anode.clause_number
        if not anode.parent.is_root and \
                anode.parent.clause_number != clause_num:
            clause_num = 0
        # add parentheses
        if not self.continued_paren_left(anode):
            left_par = self.add_parenthesis_node(anode, '(', clause_num)
            left_par.shift_before_subtree(anode)
        if not self.continued_paren_right(anode):
            right_par = self.add_parenthesis_node(anode, ')', clause_num)
            right_par.shift_after_subtree(anode)

    def add_parenthesis_node(self, anode, lemma, clause_num):
        """\
        Add a parenthesis node as a child of the specified a-node;
        with the given lemma and clause number set.
        """
        return anode.create_child(data={'lemma': lemma,
                                        'form': lemma,
                                        'afun': 'AuxX',
                                        'morphcat': {'pos': 'X'},
                                        'clause_number': clause_num})

    def continued_paren_left(self, anode):
        "Return True if this node is continuing a parenthesis from the left."
        prev = anode.get_prev_node()
        while prev and prev.afun is not None and prev.afun.startswith('Aux'):
            prev = prev.get_prev_node()
        if not prev:
            return False
        return prev.get_attr('wild/is_parenthesis')

    def continued_paren_right(self, anode):
        "Return True if a parenthesis continues after this node to the right."
        node = anode.get_next_node()
        while node and node.afun is not None and node.afun.startswith('Aux'):
            node = node.get_next_node()
        if not node:
            return False
        return node.get_attr('wild/is_parenthesis')
