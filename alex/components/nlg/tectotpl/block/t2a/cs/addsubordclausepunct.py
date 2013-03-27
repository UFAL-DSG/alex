#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
import re
from treex.block.t2a.cs.addclausalpunct import AddClausalPunct
from treex.tool.lexicon.cs import is_coord_conj

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddSubordClausePunct(AddClausalPunct):
    """
    Add commas separating subordinate clauses.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_atree(self, aroot):
        "Add subordinate clause punctuation to the given sentence."
        anodes = aroot.get_descendants(ordered=True)
        # examine all places between two nodes
        for (aleft, aright) in zip(anodes[:-1], anodes[1:]):
            # exclude all places where we don't want a comma
            # within the same clause
            if aleft.clause_number == aright.clause_number:
                continue
            # clause boundaries, such as brackets
            if aright.clause_number == 0:
                continue
            # some punctuation is here already
            if [an for an in (aleft, aright)
                    if re.match(r'^[,:;.?!-]', an.lemma)]:
                continue
            # coordinating conjunctions or nodes in clauses belonging
            # to the same coordination
            if [an for an in (aleft, aright) if is_coord_conj(an.lemma)]:
                continue
            if self.are_in_coord_clauses(aleft, aright):
                continue
            # left token is an opening quote or bracket
            if re.match(r'^[„(]', aleft.lemma):
                continue
            # right token is a closing bracket or quote followed by a period
            if aright.lemma == ')' or \
                    (aright.lemma == '“' and not aright.is_last_node() and
                     aright.get_next_node().lemma == '.'):
                continue
            # left token is a closing quote or bracket preceded by a comma
            # (which has been inserted in the last step)
            if re.match(r'^[“)]', aleft.lemma) and not aleft.is_first_node() \
                        and aright.get_prev_node().lemma == ',':
                continue
            # now we know we want to insert a comma
            acomma = self.insert_comma_between(aleft, aright)
            # move the comma if the left token marks
            # the end of an enquoted clause
            if self.is_clause_in_quotes(aleft):
                acomma.shift_before_node(aleft)
            # move the comma after clausal expletives in expression "poté co"
            if aright.lemma == 'poté':
                acomma.shift_after_node(aright)

    def are_in_coord_clauses(self, aleft, aright):
        "Check if the given nodes are in two coordinated clauses."
        alparent = self.get_clause_parent(aleft)
        arparent = self.get_clause_parent(aright)
        return alparent == arparent and \
                not alparent.is_root and is_coord_conj(alparent.lemma)

    def get_clause_parent(self, anode):
        """Return the parent of the clause the given node belongs to;
        the result may be the root of the tree."""
        if anode.clause_number == 0:
            parent = anode
        else:
            parent = anode.get_clause_root().parent
        while parent.is_coap_root() and parent.is_member:
            parent = parent.parent
        return parent

    def insert_comma_between(self, aleft, aright):
        """Insert a comma node between these two nodes,
        find out where to hang it."""
        # find out the parent
        aleft_clause_root = aleft.get_clause_root()
        aright_clause_root = aright.get_clause_root()
        ahigher_clause_root = aleft_clause_root.get_depth() > \
                aright_clause_root.get_depth() and \
                aleft_clause_root or aright_clause_root
        # insert the new node
        acomma = ahigher_clause_root.create_child(\
                         data={'form': ',', 'lemma': ',', 'afun': 'AuxX',
                               'morphcat': {'pos': 'Z'}, 'clause_number': 0})
        # shift the new node to its rightful place
        acomma.shift_after_node(aleft)
        return acomma
