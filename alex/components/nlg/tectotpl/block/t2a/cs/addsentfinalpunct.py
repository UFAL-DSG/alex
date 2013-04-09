#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

import re
from alex.components.nlg.tectotpl.block.t2a.cs.addclausalpunct import AddClausalPunct

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddSentFinalPunct(AddClausalPunct):
    """
    Add final sentence punctuation ('?', '.').

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        super(AddSentFinalPunct, self).__init__(scenario, args)

    def process_ttree(self, troot):
        "Add final punctuation to the given sentence."
        tnodes = troot.get_descendants(ordered=True)
        if not tnodes:
            return
        # check if there is no punctuation on the t-layer already
        last_tnode = tnodes[-1]
        if re.match(r'^[;:.]', last_tnode.t_lemma):
            return
        # check if a punctuation mark is needed at all
        # (i.e. it is a sentence -- has a verb)
        if not [tnode for tnode in tnodes
                if re.match(r'^v:.*fin$', tnode.formeme)]:
            return
        # decide which punctuation mark to use (question mark or dot;
        # don't use exclamation mark for imperatives)
        sent_root = troot.get_children()[0]
        punct_mark = sent_root.sentmod == 'inter' and '?' or '.'
        aroot = troot.zone.atree
        punct_anode = aroot.create_child(data={'form': punct_mark,
                                               'lemma': punct_mark,
                                               'morphcat': {'pos': 'Z'},
                                               'afun': 'AuxK',
                                               'clause_number': 0})
        # move the punctuation to the end, or before the quotation marks
        # if there's a clause in quotes
        if not tnode.lex_anode:
            return
        if self.is_clause_in_quotes(last_tnode.lex_anode):
            punct_anode.shift_before_node(last_tnode.lex_anode)
        else:
            punct_anode.shift_after_subtree(aroot)
