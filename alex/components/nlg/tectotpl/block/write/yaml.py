#!/usr/bin/env python
# coding=utf-8
#
# Block for reading Treex YAML files
#

from __future__ import absolute_import
from __future__ import unicode_literals

import yaml
from alex.components.nlg.tectotpl.block.write.basewriter import BaseWriter
import types
from alex.components.nlg.tectotpl.core.util import file_stream

__author__ = "Ondřej Dušek"
__date__ = "2012"


class YAML(BaseWriter):

    default_extension = '.yaml'

    def __init__(self, scenario, args):
        "Empty constructor (just call the base constructor)"
        BaseWriter.__init__(self, scenario, args)

    def process_document(self, doc):
        "Write a YAML document"
        data = []
        for bundle in doc.bundles:
            data.append(self.serialize_bundle(bundle))
        out = file_stream(self.get_output_file_name(doc), 'w', encoding=None)
        out.write(yaml.safe_dump(data, allow_unicode=True,
                                 explicit_start=True))
        out.close()

    def serialize_bundle(self, bundle):
        "Serialize a bundle to a list."
        return [self.serialize_zone(zone) for zone in bundle.get_all_zones()]

    def serialize_zone(self, zone):
        "Serialize a zone into a hash"
        data = {}
        if zone.sentence is not None:
            data['sentence'] = zone.sentence
        if zone.language is not None:
            data['language'] = zone.language
        if zone.selector is not None:
            data['selector'] = zone.selector
        for layer in 'a', 't', 'n', 'p':
            if zone.has_tree(layer):
                data[layer + 'tree'] = \
                        self.serialize_tree(zone.get_tree(layer))
        return data

    def serialize_tree(self, root):
        data = self.serialize_node(root, add_parent_id=False)
        data['nodes'] = [self.serialize_node(node, add_parent_id=True)
                         for node in root.get_descendants(ordered=True)]
        return data

    def serialize_node(self, node, add_parent_id):
        """\
        Serialize a node to a hash; using the correct attributes for the
        tree type given. Add the node parent's id if needed.
        """
        data = {'id': node.id}
        for attr in node.get_attr_list():
            value = node.get_attr(attr)
            # write all non-nulls, but skip empty dictionaries and lists
            if value is not None and \
                    ((type(value) != types.DictType and
                      type(value) != types.ListType and
                      type(value) != types.BooleanType) or value):
                data[attr] = value
        if add_parent_id:
            data['parent_id'] = node.parent.id
        return data
