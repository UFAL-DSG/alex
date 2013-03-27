#!/usr/bin/env python
# coding=utf-8
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class RemoveRepeatedTokens(Block):
    """\
    Remove two identical neighboring tokens.
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_zone(self, zone):
        """\
        Remove two identical neighboring tokens in the given sentence.
        """
        tokens = re.split(r'(\W+)', zone.sentence)
        sent = ''
        prev = None
        for i, token in enumerate(tokens):
            if i == 0 or re.match(r'^\s+$', token) or token.lower() != prev:
                sent += token
            if not re.match(r'^\s+$', token):
                prev = token.lower()
        # normalize accidentally messed-up spaces
        sent = re.sub(r'\s+', ' ', sent)
        sent = re.sub(r' ([.,])$', r'\1', sent)
        # assign back
        zone.sentence = sent
