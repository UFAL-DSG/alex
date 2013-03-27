#!/usr/bin/env python
# coding=utf-8
#
# Block for making tree copies
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block

__author__ = "Ondřej Dušek"
__date__ = "2012"


class SetGlobal(Block):

    def __init__(self, scenario, args):
        """\
        Constructor, sets the arguments given to this block as global.
        """
        Block.__init__(self, scenario, args)
        for arg, value in args.iteritems():
            scenario.global_args[arg] = value

    def process_bundle(self, doc):
        """\
        This block does nothing with the documents, its only work
        is setting the global arguments in the initialization phase.
        """
        pass
