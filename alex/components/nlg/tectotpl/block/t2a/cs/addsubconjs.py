#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
import re
from treex.block.t2a.addauxwords import AddAuxWords
from treex.tool.lexicon.cs import inflect_conditional

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddSubconjs(AddAuxWords):
    """
    Add subordinate conjunction a-nodes according to formemes.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def get_aux_forms(self, tnode):
        "Find prepositional nodes to be created."
        match = re.match(r'^v:(.+)\+', tnode.formeme)
        if not match:
            return None
        # obtain the surface forms of the prepositions
        return match.group(1).split('_')

    def new_aux_node(self, anode, form):
        """\
        Create a subordinate conjunction node with the given
        conjunction form and parent.
        """
        new_node = anode.create_child()
        # inflect 'aby' and 'kdyby'
        if form in ['aby', 'kdyby']:
            new_node.form = inflect_conditional(form, anode.morphcat_number,
                                                anode.morphcat_person)
        else:
            new_node.form = form
        new_node.afun = 'AuxC'
        new_node.lemma = form
        new_node.morphcat_pos = 'J'
        new_node.shift_before_subtree(anode)
        return new_node
