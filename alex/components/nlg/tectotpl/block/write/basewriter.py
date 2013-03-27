#!/usr/bin/env python
# coding=utf-8
#
# Base block for writing
#
from __future__ import unicode_literals
from treex.core.block import Block

import os
from treex.core.exception import RuntimeException

__author__ = "Ondřej Dušek"
__date__ = "2012"


class BaseWriter(Block):
    "Base block for output writing."

    def __init__(self, scenario, args):
        "Empty constructor (just call the base constructor)"
        Block.__init__(self, scenario, args)
        self.to = None
        self.path = None
        self.add_to_name = None
        if 'to' in args:
            self.to = args['to']
        elif 'path' in args:
            self.path = args['path']
        elif 'add_to_name' in args:
            self.add_to_name = args['add_to_name']

    def get_output_file_name(self, doc):
        "Create an output file name for the given document."
        if self.to:
            return self.to
        if self.path:
            _, docfilename = os.path.split(doc.filename)
            return os.path.join(self.path, docfilename)
        # try to add something to the name / change extension
        if doc.filename.endswith('.gz'):
            docfilename, docext = os.path.splitext(doc.filename[:-3])
            compress_e = '.gz'
        else:
            docfilename, docext = os.path.splitext(doc.filename)
            compress_e = ''
        if self.add_to_name:
            return docfilename + self.add_to_name + \
                self.__class__.default_extension + compress_e
        if hasattr(self.__class__, 'default_extension') and \
                self.__class__.default_extension != docext:
            return docfilename + self.__class__.default_extension + compress_e
        # no default, just die
        raise RuntimeException('I don\'t know where to write.')
