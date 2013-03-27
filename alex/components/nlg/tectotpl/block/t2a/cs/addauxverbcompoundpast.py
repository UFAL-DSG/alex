#!/usr/bin/env python
# coding=utf-8
#
# A Treex block
#
from __future__ import unicode_literals

from treex.core.block import Block
from treex.core.exception import LoadingException
import re

__author__ = "Ondřej Dušek"
__date__ = "2012"


class AddAuxVerbCompoundPast(Block):
    """
    Add compound past tense auxiliary of the 1st and 2nd person
    'jsem/jsi/jsme/jste'.

    Arguments:
        language: the language of the target tree
        selector: the selector of the target tree
    """

    AUX_PAST_FORMS = {('S', '1'): 'jsem',
                      ('S', '2'): 'jsi',
                      ('P', '1'): 'jsme',
                      ('P', '2'): 'jste',
                      ('.', '1'): 'jsem',
                      ('.', '2'): 'jsi'}  # default to sg if number is unknown

    def __init__(self, scenario, args):
        "Constructor, just checking the argument values"
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')

    def process_tnode(self, tnode):
        "Add compound past auxiliary to a node, where appropriate."
        aconj = tnode.get_deref_attr('wild/conjugated')
        # only past tense, 1st/2nd person and avoid by/aby/kdyby
        if tnode.gram_tense != 'ant' or \
                not aconj.morphcat_person in ['1', '2'] or \
                tnode.gram_verbmod == 'cdn' or \
                re.search(r'\b(aby|kdyby)\b', tnode.formeme):
            return
        # make the original verb a past participle
        aconj.morphcat_subpos = 'p'
        # create the new auxiliary node
        if aconj.afun == 'AuxV':  # auxiliary conjugated -> make it a sibling
            anew_aux = aconj.parent.create_child()
        else:  # normal verb conjugated -> make it a child
            anew_aux = aconj.create_child()
        # fill it with attributes
        anew_aux.shift_before_node(aconj)
        anew_aux.afun = 'AuxV'
        anew_aux.lemma = 'být'
        anew_aux.morphcat = {'pos': 'V', 'subpos': 'B', 'tense': 'P',
                             'person': aconj.morphcat_person,
                             'number': aconj.morphcat_number,
                             'gender': '-', 'voice': 'A', 'negation': 'A'}
        anew_aux.form = self.AUX_PAST_FORMS[(aconj.morphcat_number,
                                             aconj.morphcat_person)]
        # handle links
        tnode.set_deref_attr('wild/conjugated', anew_aux)
        tnode.add_aux_anodes(anew_aux)
