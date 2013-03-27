#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.exception import LoadingException
import re
from treex.tool.lexicon.cs import has_expletive
from treex.block.t2a.addauxwords import AddAuxWords


__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddClausalExpletives(AddAuxWords):
    """
    Add clausal expletive pronoun 'to' (+preposition) to subordinate clauses
    with 'že', if the parent verb requires it.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        super(AddClausalExpletives, self).__init__(scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def get_aux_forms(self, tnode):
        "Return the clausal expletive to be added, if supposed to."
        # no expletives needed when there is no conjunction 'že'
        # (or if they are already included in the formeme)
        if tnode.formeme != 'v:že+fin':
            return None
        # no expletives if the parent verb is not appropriate
        # TODO coordinations are not handled
        expletive = has_expletive(tnode.parent.t_lemma)
        if not expletive:
            return None
        # there should be an expletive -> return it
        return expletive.split('_')

    def new_aux_node(self, anode, form):
        "Create a node for the expletive/its preposition."
        new_node = anode.create_child()
        # expletive
        if re.match(r'^t(o|oho|mu|om|ím)', form):
            new_node.afun = 'Obj'
            new_node.lemma = 'ten'
            new_node.morphcat = {'pos': 'P', 'subpos': 'D',
                                 'gender': 'N', 'number': 'S'}
        # preposition
        else:
            new_node.afun = 'AuxP'
            new_node.lemma = form
            new_node.morphcat_pos = 'R'
        new_node.form = form
        new_node.shift_before_subtree(anode)
        return new_node

    def postprocess(self, tnode, anode, aux_anodes):
        """\
        Rehang the conjunction 'že', now above the expletive, under it.
        Fix clause numbers and ordering.
        """
        # find the conjunction 'že' and its parent
        aconj_ze = anode.parent.parent
        aparent = aconj_ze.parent
        # rehang all expletives under the parent
        aux_anodes[0].parent = aparent
        aux_anodes[0].clause_number = aparent.clause_number
        if len(aux_anodes) > 1:
            for aux in aux_anodes[1:]:
                aux.parent = aux_anodes[0]
                aux.clause_number = aparent.clause_number
        # rehang the conjunction under them
        aconj_ze.parent = aux_anodes[-1]
        # shift the conjunction after the expletive
        aconj_ze.shift_before_subtree(anode)
        # hang the dependent clause under the expletive
        anode.parent = aconj_ze

    def get_anode(self, tnode):
        "Return the a-node that is the root of the verbal a-subtree."
        if tnode.get_attr('wild/conjugated'):
            aconj = tnode.get_deref_attr('wild/conjugated')
            if aconj.afun == 'AuxV':
                return aconj.parent
            return aconj
        else:
            return tnode.lex_anode
