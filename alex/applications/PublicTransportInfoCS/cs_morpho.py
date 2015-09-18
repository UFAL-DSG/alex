#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

"""Wrappers for Morphodita Czech morphology analyzer and generator."""

from ufal.morphodita import Tagger, Forms, TaggedLemmas, TokenRanges, Morpho, TaggedLemmasForms
import re


class Analyzer(object):
    """Morphodita analyzer/tagger wrapper."""

    def __init__(self, tagger_model):
        self.__tagger = Tagger.load(tagger_model)
        self.__tokenizer = self.__tagger.newTokenizer()
        self.__forms_buf = Forms()
        self.__tokens_buf = TokenRanges()
        self.__lemmas_buf = TaggedLemmas()

    def analyze(self, stop_text):
        self.__tokenizer.setText(stop_text)
        while self.__tokenizer.nextSentence(self.__forms_buf, self.__tokens_buf):
            self.__tagger.tag(self.__forms_buf, self.__lemmas_buf)
            return [(form, lemma.lemma, lemma.tag)
                    for (form, lemma) in zip(self.__forms_buf, self.__lemmas_buf)]


class Generator(object):
    """Morphodita generator wrapper, with support for inflecting
    noun phrases (stop/city names, personal names)."""

    def __init__(self, morpho_model):
        self.__morpho = Morpho.load(morpho_model)
        self.__out_buf = TaggedLemmasForms()

    def generate(self, lemma, tag_wildcard, capitalized=None):
        """Get variants for one word from the Morphodita generator. Returns
        empty list if nothing found in the dictionary."""
        # run the generation for this word
        self.__morpho.generate(lemma, tag_wildcard, self.__morpho.GUESSER, self.__out_buf)
        # see if we found any forms, return empty if not
        if not self.__out_buf:
            return []
        # prepare capitalization
        cap_func = lambda string: string
        if capitalized == True:
            cap_func = lambda string: string[0].upper() + string[1:]
        elif capitalized == False:
            cap_func = lambda string: string[0].lower() + string[1:]
        # process the results
        return [cap_func(form_tag.form) for form_tag in self.__out_buf[0].forms]

    def inflect(self, words, case, personal_names=False, check_fails=False):
        """Inflect a stop/city/personal name in the given case (return 
        lists of inflection variants for all words).
        
        @param words: list of form/lemma/tag triplets from the analyzer to be inflected
        @param case: the target case (Czech, 1-7)
        @param personal_names: should be False for stops/cities, True for personal names
        @param check_fails: if True, return None if the form is not in the dictionary"""
        forms = []
        prev_tag = ''
        for word in words:
            form_list = self.__inflect_word(word, case, prev_tag)
            if not form_list:
                if check_fails:
                    return None
                form_list = [word[0]]
            forms.append(form_list)
            prev_tag = word[2]
        return forms

    def __inflect_word(self, word, case, prev_tag, personal_names=False):
        """Inflect one word in the given case (return a list of variants,
        None if the generator fails)."""
        form, lemma, tag = word
        # inflect each word in nominative not following a noun in nominative
        # (if current case is not nominative), avoid numbers
        if (re.match(r'^[^C]...1', tag) and
                (not re.match(r'^NN..1', prev_tag) or personal_names) and
                form not in ['římská'] and
                case != '1'):
            # change the case in the tag, allow all variants
            new_tag = re.sub(r'^(....)1(.*).$', r'\g<1>' + case + r'\g<2>?', tag)
            # -ice: test both sg. and pl. versions
            if (form.endswith('ice') and form[0] == form[0].upper() and
                    not re.match(r'(nemocnice|ulice|vrátnice)', form, re.IGNORECASE)):
                new_tag = re.sub(r'^(...)S', r'\1[SP]', new_tag)
            # try inflecting, return empty list if not found in the dictionary
            capitalized = form[0] == form[0].upper()
            new_forms = self.generate(lemma, new_tag, capitalized)
            return new_forms
        else:
            return [form]

