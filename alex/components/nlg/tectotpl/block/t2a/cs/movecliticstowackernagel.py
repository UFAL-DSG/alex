#!/usr/bin/env python
# coding=utf-8
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
from alex.components.nlg.tectotpl.core.util import first

__author__ = "Ondřej Dušek"
__date__ = "2012"


class MoveCliticsToWackernagel(Block):
    """\
    Move clitics (e.g. 'se', 'to' etc.) to the second (Wackernagel) position
    in the clause.
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_atree(self, aroot):
        """\
        Process the individual clauses -- find and move clitics within them.
        """
        # Divide nodes into clauses
        clauses = {}
        for anode in aroot.get_descendants(ordered=True):
            if not anode.clause_number:
                continue
            clause = clauses.get(anode.clause_number, [])
            clauses[anode.clause_number] = clause
            clause.append(anode)
        # Process all clauses
        for clause in clauses.itervalues():
            self.process_clause(clause)

    def process_clause(self, clause):
        """\
        Find and move clitics within one clause.
        """
        # find if we have any clitics to process, sort them
        clitics = [anode for anode in clause if self.is_clitic(anode)]
        clitics.sort(key=self.clitic_order, reverse=True)
        if not clitics:
            return
        # handle cases where clitics should not be moved
        clause_root = clause[0].get_clause_root()
        if clause_root.form == 'je' and clause_root.lemma == 'být':
            clitics = [c for c in clitics if not self.handle_pronoun_je(c)]
        # filter out clitics belonging to nested infinitives etc.
        clitics = [c for c in clitics
                   if self.verb_group_root(c) == clause_root]
        if not clitics:
            return
        # find the word directly preceding Wackernagel position
        have_coord = self.is_coord_taking_1st_pos(clause_root)
        first = self.find_eo1st_pos(clause_root, clause[0]) \
                if not have_coord else None
        # shift clitics
        # if there is a coordination at the 1st position
        if have_coord:
            for clitic in clitics:
                clitic.shift_before_subtree(clause_root, without_children=True)
        # after the 1st word if it is the clause root
        elif first == clause_root:
            for clitic in clitics:
                clitic.shift_after_node(first, without_children=True)
        # after the subtree of the 1st word
        else:
            for clitic in clitics:
                clitic.shift_after_subtree(first, without_children=True)

    def handle_pronoun_je(self, anode):
        """\
        If the given node is a personal pronoun with the form 'je',
        move it before its parent's subtree and return True.
        Return false otherwise.
        """
        if anode.form == 'je' and anode.morphcat_subpos == 'P':
            anode.shift_before_subtree(anode.parent)
            return True
        return False

    def clitic_order(self, clitic):
        """\
        Return the position of the given clitic in the
        natural Czech order of multiple clitics in the same clause.
        """
        form = clitic.form.lower()
        if form in {'jsem', 'jsme', 'jsi', 'jste',
                    'by', 'bych', 'bys', 'bychom', 'byste'}:
            return 1
        elif form in {'se', 'si'}:
            return 2
        elif form in {'mi', 'ti', 'mu', 'jí', 'nám', 'vám', 'jim'}:
            return 3
        elif form in {'mě', 'tě', 'ho', 'ji', 'nás', 'vás', 'je', 'to'}:
            return 4
        elif form in {'tam', 'sem'}:
            return 6
        else:  # ses sis bychom mně tobě jemu
            return 5

    def is_coord_taking_1st_pos(self, clause_root):
        """\
        Return True if the clause root is a coordination member and the
        coordinating conjunction or shared subjunction is taking up the 1st
        position.
        E.g. 'Běžel, aby se zahřál a dostal se dřív domů.'
        """
        coap = clause_root.parent
        # find out if we have a coordination with some members
        if not coap or not coap.is_coap_root:
            return False
        eparents = clause_root.get_eparents()
        if not eparents or eparents[0].afun != 'AuxC':
            return False
        coord_members = [c for c in coap.get_children(ordered=True)
                         if c.is_member]
        if not coord_members:
            return False
        # only fire for the first and last coordination members,
        # exclude 'a' and 'ale'
        return clause_root == coord_members[0] or \
                clause_root == coord_members[-1] and \
                coap.lemma not in {'a', 'ale'}

    def find_eo1st_pos(self, clause_root, clause_1st):
        """\
        Find the last word before the Wackernagel position.
        """
        # leftmost node is the root -- typical for subordinating
        # conjunctions (leave out the multi-word ones)
        if (clause_root == clause_1st and
            not [c for c in clause_root.get_children() if c.afun == 'AuxC']):
            return clause_root
        # otherwise return one of the clause root's children
        num = clause_root.clause_number
        return first(lambda node: not self.should_ignore(node, num),
                     clause_root.get_children(ordered=True, add_self=True),
                     clause_root)

    def verb_group_root(self, clitic):
        """\
        Find the root of the verbal group that the given clitic belongs to.
        If the verbal group is governed by a conjunction, return this
        conjunction.
        """
        verb_root = clitic
        # climb up as long as we don't leave the clause and there are only
        # verbs along the path
        while True:
            parent = verb_root.parent
            if parent.is_root or \
                    parent.clause_number != verb_root.clause_number or \
                    (parent.morphcat_pos != 'V' and
                     parent.lemma not in {'vědomý', 'jistý'}):
                break
            verb_root = parent
        # check for conjunctions
        if not verb_root.is_root and verb_root.parent.afun == 'AuxC':
            return verb_root.parent
        return verb_root

    def is_clitic(self, anode):
        """\
        Return True if the given node belongs to a clitic.
        """
        subpos, case, afun, form = anode.morphcat_subpos, \
                anode.morphcat_case, anode.afun, anode.form.lower()
        # 7 - reflexive pronouns, H - short forms of personal pronouns,
        # c - conditional particles
        if subpos in {'7', 'H', 'c'}:
            return True
        # direct object personal pronouns in dative or accusative
        if subpos == 'P' and case in {'3', '4'} and not anode.is_member and \
                anode.parent.morphcat_pos == 'V':
            return True
        # forms of the auxiliary 'být'
        if afun == 'AuxV' and form in {'jste', 'jsme', 'jsem', 'jsi'}:
            return True
        # the pronoun 'to' as direct object or nominal predicate
        if form == 'to' and anode.parent.morphcat_pos == 'V' and \
                (case == '4' or (case == '1' and anode.parent.lemma == 'být')):
            return True
        # 'tam', 'sem'
        return form in {'sem', 'tam'}

    def should_ignore(self, anode, clause_number):
        """\
        Return True if this word should be ignored in establishing the
        Wackernagel position.
        """
        # clitics, subordinate clauses
        if self.is_clitic(anode) or anode.clause_number != clause_number:
            return True
        # punctuation
        if anode.morphcat_pos == 'Z':
            return True
        # 'a', 'ale' bound to preceding context
        if anode.lemma in {'a', 'ale'} and not anode.get_children():
            return True
        # multi-word coordinating conjunctions
        if anode.afun == 'AuxC':
            anext = anode.get_next_node()
            if anext and anext.afun == 'AuxC':
                return True
        return False
