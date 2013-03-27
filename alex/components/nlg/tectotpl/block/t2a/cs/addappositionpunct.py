#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
from treex.tool.lexicon.cs import is_personal_role, is_named_entity_label
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddAppositionPunct(Block):
    """
    Separating Czech appositions, such as in 'John, my best friend, ...' with
    commas.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_tnode(self, tnode):
        "Adds punctuation a-nodes if the given node is an apposition node."
        tparent = tnode.parent
        # the apposition is correctly parsed on t-layer
        if tnode.functor == 'APPS':
            # just add second comma
            acomma = self.add_comma_node(tnode.lex_anode)
            acomma.shift_after_subtree(tnode.lex_anode)
        # the apposition is expressed as n:attr on the t-layer, where the
        # attribute is a named entity label
        # and follows its parent, which is also a noun.
        elif tnode.formeme == 'n:attr' and tnode.gram_sempos == 'n.denot' and \
                tparent < tnode and tparent.formeme.startswith('n:') and \
                (is_personal_role(tnode.t_lemma) or
                 is_named_entity_label(tnode.t_lemma)):
            # create the apposition on the t-layer
            tgrandpa = tparent.parent
            tapp = tgrandpa.create_child(data={'functor': 'APPS',
                                               't_lemma': ';',
                                               'nodetype': 'coap'})
            tapp.shift_before_subtree(tnode)
            tparent.parent = tapp
            tnode.parent = tapp
            # create the apposition on the a-layer
            # TODO hang under the apposition not only the lex_anode,
            # but also aux anodes (if they are above lex_anode).
            agrandpa = tgrandpa.lex_anode if tgrandpa.lex_anode \
                    else tnode.lex_anode.root
            aapp_left = self.add_comma_node(agrandpa)
            aapp_left.afun = 'Apos'
            aapp_left.shift_before_subtree(tnode.lex_anode)
            tnode.lex_anode.parent = aapp_left
            tnode.lex_anode.is_member = True
            tparent.lex_anode.parent = aapp_left
            tparent.lex_anode.is_member = True
            tapp.lex_anode = aapp_left
            # create right comma
            if not self.is_before_punct(tnode.lex_anode):
                aapp_right = self.add_comma_node(aapp_left)
                aapp_right.shift_after_subtree(tnode.lex_anode)
                tapp.add_aux_anodes(aapp_right)

    def add_comma_node(self, aparent):
        "Add a comma a-node to the given parent"
        return aparent.create_child(data={'lemma': ',',
                                          'form': ',',
                                          'afun': 'AuxX'})

    def is_before_punct(self, anode):
        """\
        Test whether the subtree of the given node
        precedes a punctuation node.
        """
        next_node = anode.get_descendants(add_self=True,
                                          ordered=True)[-1].get_next_node()
        return not next_node or re.match(r'[;.,?!„“‚‘"]', next_node.lemma)
