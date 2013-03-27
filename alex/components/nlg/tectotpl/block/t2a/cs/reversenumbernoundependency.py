#!/usr/bin/env python
# coding=utf-8
#
# Creating an a-tree from a t-tree.
#
from __future__ import unicode_literals
from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core.exception import LoadingException
import re
from alex.components.nlg.tectotpl.tool.lexicon.cs import Lexicon

__author__ = "Ondřej Dušek"
__date__ = "2012"


class ReverseNumberNounDependency(Block):
    """
    This block reverses the dependency of incongruent Czech numerals (5 and
    higher), hanging their parents under them in the a-tree.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    def __init__(self, scenario, args):
        "Constructor, checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')
        self.lexicon = Lexicon()

    def process_ttree(self, ttree):
        "Rehang the numerals for the given t-tree & a-tree pair"
        for tnode in ttree.get_children():
            self.__process_subtree(tnode)

    def __process_subtree(self, tnode):
        "Process the subtree of the given node"
        # solve the current node
        if tnode.is_coap_root():
            self.__process_coap_tnode(tnode)
        else:
            self.__process_plain_tnode(tnode)
        # recurse deeper
        for child in tnode.get_children():
            self.__process_subtree(child)

    def __process_plain_tnode(self, tnode):
        "Process a normal (non-coap) tnode"
        tnoun = tnode.parent
        # filter out cases where we don't need to do anything: lemma, case
        if tnoun < tnode or not self.__should_reverse(tnode.t_lemma):
            return
        noun_prep, noun_case = self.__get_prepcase(tnoun)
        if noun_case is None or noun_case not in ['1', '4']:
            return
        # make the switch
        self.__swap_anodes(tnode, tnoun)
        self.__update_formemes(tnode, tnoun, noun_prep, noun_case)
        # make the objects singular for Czech decimal numbers
        if re.match(r'^\d+[,.]\d+$', tnode.t_lemma):
            tnode.gram_number = 'sg'

    def __process_coap_tnode(self, tnode):
        "Process a coap root"
        # check if we have actually something to process
        tchildren = [tchild for tchild in tnode.get_children(ordered=1)
                     if tchild.is_member]
        if not tchildren:
            return
        # check whether the switch should apply to all children
        tnoun = tnode.parent
        if tnoun < tnode or filter(lambda tchild:
                                   not self.__should_reverse(tchild.t_lemma),
                                   tchildren):
            return
        # check noun case
        noun_prep, noun_case = self.__get_prepcase(tnoun)
        if noun_case is None or noun_case not in ['1', '4']:
            return
        # switch the coap root with the noun
        self.__swap_anodes(tnode, tnoun)
        for tchild in tchildren:
            self.__update_formemes(tchild, tnoun, noun_prep, noun_case)
        # fix object number according to the last child
        if re.match(r'^\d+[,.]\d+$', tchildren[-1].t_lemma):
            tnode.gram_number = 'sg'

    def __update_formemes(self, tnumber, tnoun, noun_prep, noun_case):
        "Update the formemes to reflect the swap of the nodes"
        # merge number and noun prepositions
        number_prep = re.search(r'(?::(.*)\+)?', tnumber.formeme).group(1)
        if noun_prep and number_prep:
            preps = noun_prep + '_' + number_prep + '+'
        elif noun_prep or number_prep:
            preps = (noun_prep or number_prep) + '+'
        else:
            preps = ''
        # mark formeme origins for debugging
        tnoun.formeme_origin = 'rule-number_from_parent(%s : %s)' % \
                (tnoun.formeme_origin, tnoun.formeme)
        tnumber.formeme_origin = 'rule-number_genitive'
        # Change formemes:
        # number gets merged preposition + noun case, noun gets genitive
        tnumber.formeme = 'n:%s%s' % (preps, noun_case)
        tnoun.formeme = 'n:2'

    def __swap_anodes(self, tnumber, tnoun):
        "Swap the dependency between a number and a noun on the a-layer"
        # the actual swap
        anumber = tnumber.lex_anode
        anoun = anumber.parent
        anumber.parent = anoun.parent
        anoun.parent = anumber
        # fix is_member
        if anoun.is_member:
            anoun.is_member = False
            anumber.is_member = True
        # fix parenthesis
        if anoun.get_attr('wild/is_parenthesis'):
            anoun.set_attr('wild/is_parenthesis', False)
            anumber.set_attr('wild/is_parenthesis', True)

    def __get_prepcase(self, tnoun):
        """\
        Return the preposition and case of a noun formeme
        if the case is nominative or accusative. Returns None otherwise.
        """
        try:
            return re.search(r'^n:(?:(.*)\+)?([14X])$', tnoun.formeme).groups()
        except:
            return None, None

    def __should_reverse(self, lemma):
        """\
        Return true if the given lemma belongs to an incongruent numeral.
        This is actually a hack only to allow for translation of
        the English words "most" and 'more'. Normally, the method
        is_incongruent_numeral should be used directly.
        """
        if is_incongruent_numeral(lemma) or lemma in ['většina', 'menšina']:
            return True
        return False
