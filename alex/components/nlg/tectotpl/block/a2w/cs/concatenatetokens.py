#!/usr/bin/env python
# coding=utf-8
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class ConcatenateTokens(Block):
    """\
    Detokenize the sentence, spread whitespace correctly.
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_zone(self, zone):
        """\
        Detokenize the sentence and assign the result to the sentence attribute
        of the current zone.
        """
        aroot = zone.atree
        sent = ' '.join([a.form for a
                         in aroot.get_descendants(ordered=True)
                         if a.form and not re.match(r'^(#[A-Z]|[A-Z]{3}$)',
                                                    a.form)])
        # whitespace around punctuation
        sent = re.sub(r' ([“,.?:;])', r'\1', sent)
        sent = re.sub(r'(["“])\.', r'.\1', sent)
        sent = re.sub(r'„ ', r'„', sent)
        # normalizing
        sent = re.sub(r' -- ', r' – ', sent)
        sent = re.sub(r'_', r' ', sent)
        # space around parentheses
        sent = re.sub(r',?\(,? ?', r'(', sent)
        sent = re.sub(r' ?,? ?\)', r')', sent)
        if sent.startswith('('):
            sent = re.sub(r'\)\.', r'.)', sent)
        zone.sentence = sent
