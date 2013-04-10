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


class AddClausalPunct(Block):
    """
    An abstract ancestor for blocks working with clausal punctuation.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def is_clause_in_quotes(self, anode):
        """\
        Return True if the given node is in an enquoted clause.
        The node must end the clause.
        """
        # a complete enquoted clause at the end
        aclause_root = anode.get_clause_root()
        aclause_nodes = aclause_root.get_children(add_self=True, ordered=True)
        if len(aclause_nodes) >= 2 \
            and re.match(r'[“‘\']', aclause_nodes[-1].lemma) \
            and re.match(r'[„‚\']', aclause_nodes[0].lemma):
            return True
        # the only punctuation mark, i.e. whole sentence is a part of a
        # longer speech etc.
        if [an for an in anode.root.get_descendants()
            if re.match(r'[„‚“‘\']', an.lemma)] == [anode]:
            return True
        # default to False
        return False
