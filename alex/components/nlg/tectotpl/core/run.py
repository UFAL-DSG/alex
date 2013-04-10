#!/usr/bin/env python
# coding=utf-8
#
# Classes related to Treex runs
#
from __future__ import unicode_literals
import sys
import codecs
from alex.components.nlg.tectotpl.core import ScenarioException
from alex.components.nlg.tectotpl.core.log import log_info
from io import StringIO

__author__ = "Ondřej Dušek"
__date__ = "2012"


class Scenario(object):
    """This represents a scenario, i.e. a sequence of
    blocks to be run on the data"""

    def __init__(self, config):
        "Initialize (parse YAML scenario from a file)"
        # initialize global arguments
        self.global_args = config.get('global_args', {})
        self.scenario_data = config.get('scenario')
        self.data_dir = config.get('data_dir')
        # check whether scenario contains blocks
        if not self.scenario_data:
            raise ScenarioException('No blocks in scenario')
        if not self.data_dir:
            raise ScenarioException('Data directory must be set')

    def load_blocks(self):
        "Load all blocks into memory, finding and creating class objects."
        self.blocks = []
        for block_no, block_data in enumerate(self.scenario_data, start=1):
            # create the block name and import it
            if '.' in block_data["block"]:
                class_subpath, class_name = block_data["block"].rsplit('.', 1)
                class_subpath += '.'
            else:
                class_subpath, class_name = '', block_data["block"]
            class_package = 'alex.components.nlg.tectotpl.block.' \
                    + class_subpath + class_name.lower()
            log_info('Loading block ' + str(block_no) + '/' +
                     str(len(self.scenario_data)) + ': ' + class_name)
            exec('import ' + class_package)
            class_obj = getattr(sys.modules[class_package], class_name)
            # create the block object
            args = self.global_args.copy()
            args.update(block_data.get("args", {}))
            self.blocks.append(class_obj(self, args))
            # load models etc.
            self.blocks[-1].load()

    def apply_to(self, string, language=None, selector=None):
        """
        Apply the whole scenario to a string (which should be readable by
        the first block of the scenario), return the sentence(s) of the
        given target language and selector.
        """
        # check if we know the target language and selector
        language = language or self.global_args['language']
        selector = selector or self.global_args.get('selector', '')
        # the first block is supposed to be a reader which creates the document
        fh = StringIO(string)
        doc = self.blocks[0].process_document(fh)
        # apply all other blocks
        for block_no, block in enumerate(self.blocks[1:], start=2):
            log_info('Applying block ' + str(block_no) + '/' +
                     str(len(self.blocks)) + ': ' + block.__class__.__name__)
            block.process_document(doc)
        # return the text of all bundles for the specified sentence
        return "\n".join([b.get_zone(language, selector).sentence
                          for b in doc.bundles])
