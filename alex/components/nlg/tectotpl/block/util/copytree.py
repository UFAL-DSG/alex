#!/usr/bin/env python
# coding=utf-8
#
# Block for making tree copies
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException, RuntimeException
import copy

__author__ = "Ondřej Dušek"
__date__ = "2012"


class CopyTree(Block):
    """
    This block is able to copy a tree on the same layer from a different zone.
    
    Arguments:
        language: the language of the TARGET zone
        selector: the selector of the TARGET zone
        source_language the language of the SOURCE zone (defaults to same as target)
        source_selector the selector of the SOURCE zone (defaults to same as target)
        layer: the layer to which this conversion should be applied
    
    TODO: apply to more layers at once
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None: 
            raise LoadingException('Language must be defined!')
        self.source_language = args.get('source_language') or self.language
        self.source_selector = args.get('source_selector')
        if self.source_selector is None: self.source_selector = self.selector
        if self.language == self.source_language and self.selector == self.source_selector:
            raise LoadingException('Can\'t copy tree: destination and source zones are the same!')
        self.layer = args.get('layer')
        if not self.layer:
            raise LoadingException('Can\'t copy tree: layer must be given!')
        
    def process_bundle(self, bundle):
        "For each bundle, copy the tree on the given layer in the given zone to another zone."
        if not bundle.has_zone(self.source_language, self.source_selector):
            raise RuntimeException('Bundle does not have a zone at ' + self.source_language + ', ' + self.source_selector)
        source_zone = bundle.get_zone(self.source_language, self.source_selector)
        target_zone = bundle.get_or_create_zone(self.language, self.selector)
        if not source_zone.has_tree(self.layer):
            raise RuntimeException('Source zone does not have a tree at ' + self.layer + '-layer')
        source_tree = source_zone.get_tree(self.layer)
        target_tree = target_zone.create_tree(self.layer)
        self.copy_subtree(source_tree, target_tree)
        
    def copy_subtree(self, source_root, target_root):
        "Deep-copy a subtree, creating nodes with the same attributes, but different IDs"
        # copy the current node
        for attrib_name in source_root.get_attr_list():
            target_root.set_attr(attrib_name, copy.deepcopy(source_root.get_attr(attrib_name)))
        # copy all children
        for child in source_root.get_children():
            self.copy_subtree(child, target_root.create_child()) 
        
        
        