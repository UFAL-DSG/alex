#!/usr/bin/env python
# coding=utf-8
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class DeleteSuperfluousAuxs(Block):
    """\
    Delete repeated prepositions and and conjunctions in coordinations.
    """

    DIST_LIMIT = {'v': 5, 'mezi': 50, 'pro': 8, 'protože': 5}
    BASE_DIST_LIMIT = 8

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_tnode(self, tnode):
        """\
        Check for repeated prepositions and and conjunctions in coordinations,
        delete them if necessary.
        """
        # find coordinated prepositions and conjunctions
        if not tnode.is_coap_root:
            return
        tmem = [t for t in tnode.get_children(ordered=True) if t.is_member]
        auxs = [a for t in tmem if t.aux_anodes
                for a in t.aux_anodes if a.afun in ['AuxC', 'AuxP']]
        if len(auxs) < 2:
            return
        # find the ones to delete (end for long distances or different lemmas)
        aux1 = auxs[0]
        prev_ord = aux1.ord
        limit = self.DIST_LIMIT.get(aux1.lemma, self.BASE_DIST_LIMIT)
        for aux in auxs[1:]:
            if prev_ord + limit < aux.ord or aux.lemma != aux1.lemma:
                return
            prev_ord = aux.ord
        # rehang the first aux above the coordination node
        coord = aux1.parent
        above = coord.parent
        for aux_child in [a for a in aux1.get_children()
                          if a.afun not in [aux1.afun, 'AuxX', 'AuxG']]:
            aux_child.parent = coord
            aux_child.is_member = aux1.is_member
        aux1.parent = above
        aux1.is_member = coord.is_member
        aux1.clause_number = coord.clause_number
        aux1.shift_before_subtree(coord)
        coord.is_member = False
        coord.parent = aux1
        # delete the remaining ones
        for aux in auxs[1:]:
            for aux_child in aux.get_children():
                aux_child.parent = aux.parent
                aux_child.is_member = aux.is_member
            aux.remove()
