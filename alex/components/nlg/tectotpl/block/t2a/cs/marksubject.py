#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re


__author__ = "Ondřej Dušek"
__date__ = "2012"


class MarkSubject(Block):
    """
    Marks the subject of each clause with the Afun 'Sb'.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_ttree(self, ttree):
        "Mark all subjects in a sentence"
        # filter out oblique casus and TWHEN etc. expressions,
        # e.g. "minulé pondělí" etc. and create a set of viable a-nodes
        nominatives = set([cand.lex_anode for cand in ttree.get_descendants()
                           if cand.formeme in ['n:1', 'drop'] and
                           not cand.functor.startswith('T')])
        # find all verbs and mark subjects for each of them
        for tnode in filter(lambda t: re.match(r'^v.+(fin|rc)$', t.formeme),
                            ttree.get_descendants()):
            if tnode.lex_anode:
                asubj = self.__find_subject(tnode.lex_anode, nominatives)
                if asubj is not None:
                    asubj.afun = 'Sb'

    def __find_subject(self, anode, nominatives):
        """\
        Mark subjects of a verbal node (only if they are in the candidate set)
        """
        # select all children in the right order
        candidates = list(reversed(anode.get_echildren(preceding_only=True))) \
                + anode.get_echildren(following_only=True)
        # discard those which are not "proper" nominatives,
        # return if nothing remains
        candidates = filter(lambda a: a in nominatives, candidates)
        # filter copula verb candidates - demonstrative pronouns
        if anode.lemma == 'být':
            candidates = filter(lambda a: a.lemma not in ['ten', 'tento'],
                                candidates)
        # return the first (i.e. best) candidate, if available
        return candidates[0] if candidates else None
