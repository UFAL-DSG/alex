#!/usr/bin/env python
# coding=utf-8
#
# Block for reading Treex YAML files
#
from __future__ import absolute_import
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core import Document

import yaml
from treex.core.util import file_stream

__author__ = "Ondřej Dušek"
__date__ = "2012"


class YAML(Block):

    def __init__(self, scenario, args):
        "Empty constructor (just call the base constructor)"
        Block.__init__(self, scenario, args)

    def process_document(self, filename):
        "Read a YAML file and return its contents as a Document object"
        f = file_stream(filename, encoding=None)
        data = yaml.load(f)
        doc = Document(filename, data)
        f.close()
        return doc
