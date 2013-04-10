#!/usr/bin/env python
# coding=utf-8
#
# Block for arbitrary code evaluation
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException

__author__ = "Ondřej Dušek"
__date__ = "2012"


class Eval(Block):
    """
    This block executes arbitrary Python code for each document/bundle or each zone/tree/node matching the
    current language and selector.
    
    Arguments:
        document, bundle, zone, atree, anode, ttree, tnode, ntree, nnode, ptree, pnode: code to execute
            for each <name of the argument>
            
    Arguments may be combined, but at least one of them must be set. If only X<tree/node> are set,
    language and selector is required.    
    """    
    
    # list of valid arguments to be cheked in the constructor
    valid_args = ['document', 'doc', 'bundle', 'zone', 'atree', 'anode', 
                  'ttree', 'tnode', 'ntree', 'nnode', 'ptree', 'pnode']

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        # just check if there is any valid argument in the argument dictionary 
        if not [True for arg in args.keys() if arg in self.__class__.valid_args]:
            raise LoadingException('No valid argument given (document, bundle, zone, X(tree|node)')        
    
        
    def process_document(self, doc):
        "Process a document (execute code from the 'document' argument and dive deeper)"
        code = self.args.get('document') or self.args.get('doc')
        if code is not None: 
            document = doc # provide the same variable under two names
            exec code
        # process all bundles
        super(Eval, self).process_document(doc)
    
    
    def process_bundle(self, bundle):
        "Process a document (execute code from the 'bundle' argument and dive deeper)"
        code = self.args.get('bundle')
        if code is not None: exec code
        super(Eval, self).process_bundle(bundle)
        
    def process_zone(self, zone):
        "Process a zone (according to language and selector; execute code for the zone or X<tree|node>) arguments)"
        # code for the whole zone
        code = self.args.get('zone')
        if code is not None: exec code
        # trees/nodes        
        for layer in ['a', 't', 'n', 'p']:
            # code for Xtree
            code = self.args.get(layer + 'tree')
            if code is not None:
                exec layer + 'tree = zone.get_tree(layer)' + "\n" + code
            # code for Xnode
            code = self.args.get(layer + 'node')
            if code is not None:
                for node in zone.get_tree(layer).get_descendants():
                    exec layer + 'node = node' + "\n" + code
        
    