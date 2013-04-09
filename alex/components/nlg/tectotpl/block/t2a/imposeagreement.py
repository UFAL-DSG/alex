#!/usr/bin/env python
# coding=utf-8
#
# A treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException


__author__ = "Ondřej Dušek"
__date__ = "2012"


class ImposeAgreement(Block):
    """
    A common ancestor for blocks that impose a grammatical agreement of some kind:
    they should override the should_agree(tnode), process_excepts(tnode), and impose(tnode)
    methods. 
    
    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """
    
    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None: 
            raise LoadingException('Language must be defined!')
        

    def process_tnode(self, tnode):
        "Impose the required agreement on a node, if applicable."
        match_nodes = self.should_agree(tnode)
        if match_nodes:
            self.process_excepts(tnode, match_nodes) or self.impose(tnode, match_nodes)


    def should_agree(self, tnode):
        "Check whether the agreement applies to the given node; if so, return the relevant nodes this node should agree with."
        raise NotImplementedError
    
    def process_excepts(self, tnode, match_nodes):
        "Process exceptions from the agreement. If an exception has been found and impose() should not fire, return True."
        raise NotImplementedError
    
    def impose(self, tnode, match_nodes):
        "Impose the agreement onto the given (regular) node."
        raise NotImplementedError