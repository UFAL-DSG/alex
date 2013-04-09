#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException

__author__ = "Ondřej Dušek"
__date__ = "2012"


class ProjectClauseNumber(Block):
    """
    Project clause numbering from t-nodes to a-nodes.

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
        "Project the t-node's clause number to all its corresponding a-nodes."
        for anode in tnode.anodes:
            anode.clause_number = tnode.clause_number
