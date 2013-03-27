#!/usr/bin/env python
# coding=utf-8
#
# Common ancestor for Treex blocks
#
from __future__ import unicode_literals
from treex.core.exception import RuntimeException

__author__ = "Ondřej Dušek"
__date__ = "2012"


class Block(object):
    "A common ancestor to all Treex processing blocks."
    
    def __init__(self, scenario, args):
        "Constructor, to be overridden by child blocks."
        self.scenario = scenario
        self.args = args
        self.language = args.get("language", None)
        self.selector = args.get("selector", '')
    
        
    def load(self):
        "Load required files / models, to be overridden by child blocks."
        pass
    
    
    def process_document(self, doc):
        """Process a document. Default behavior is to look for methods that process a bundle/zone/tree/node. 
        If none is found, raise a NotImplementedError"""
        for bundle in doc.bundles: self.process_bundle(bundle)
    
        
    def process_bundle(self, bundle):
        """Process a bundle. Default behavior is to process the zone according to the current language and 
        selector."""
        if self.language is None: raise RuntimeException('Undefined language')
        # select the zone and process it
        self.process_zone(bundle.get_zone(self.language, self.selector))
    
        
    def process_zone(self, zone):
        """Process a zone. Default behavior is to try if there is a process_Xtree or process_Xnode method
        and run this method, otherwise raise an error."""
        processed = False
        for layer in 'a', 't', 'n', 'p': processed = processed or self.__try_process_layer(zone, layer)
        
        
    def __try_process_layer(self, zone, layer):
        "Try to process the given layer; return True if anything was processed, false otherwise"
        if not zone.has_tree(layer): return False
        # try process_Xtree
        try:
            proc = getattr(self, 'process_' + layer + 'tree')
        except: # continue to process_Xnode, if not found
            try:
                proc = getattr(self, 'process_' + layer + 'node')
            except:
                return False
            # found process_Xnode - exec it; process self only in p-layer
            nodes = zone.get_tree(layer).get_descendants(add_self=(layer == 'p' and True or False))
            map(proc, nodes)
            return True 
        # found process_Xtree - exec it               
        proc(zone.get_tree(layer))
        return True

