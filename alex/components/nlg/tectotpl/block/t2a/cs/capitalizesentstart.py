#!/usr/bin/env python
# coding=utf-8
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re
from alex.components.nlg.tectotpl.core.util import first

__author__ = "Ondřej Dušek"
__date__ = "2012"


class CapitalizeSentStart(Block):
    """\
    Capitalize the first word in the sentence (skip punctuation etc.).
    """
    OPEN_PUNCT = r'^[({[‚„«‹|*"\']+$'

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_zone(self, zone):
        """\
        Find the first valid word in the sentence and capitalize it.
        """
        aroot = zone.atree
        troot = zone.ttree
        # take the first non-technical root (assume other to be parsing errors)
        sent_roots = aroot.get_children(ordered=True)
        if sent_roots:
            sent_roots = sent_roots[0:1]
        # add all direct speech roots
        sent_roots.extend([t.lex_anode for t in troot.get_descendants()
                           if t.is_dsp_root and t.lex_anode])
        # capitalize the 1st words under the selected roots
        for sent_root in sent_roots:
            # find the first word
            word1 = first(lambda n: n.morphcat_pos != 'Z' and
                          not re.match(self.OPEN_PUNCT,
                                       n.form or n.lemma or ''),
                          sent_root.get_descendants(ordered=True,
                                                    add_self=True))
            # skip empty sentences
            if not word1 or not word1.form:
                continue
            # compensate wrong parses in direct speech: check if the node
            # either starts the sentence or follows punctuation
            word0 = word1.get_prev_node()
            if word0 and word0.morphcat_pos != 'Z' and \
                    not re.match(self.OPEN_PUNCT,
                                 word0.form or word0.lemma or ''):
                continue
            # make it uppercase
            word1.form = word1.form[0].upper() + word1.form[1:]
