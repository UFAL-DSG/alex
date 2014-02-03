#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Expanding Czech stop/city names with inflection forms in all given morphological cases.

Usage:

./expand_stops.py [-c 1,2,4] [-m previous.expanded.txt] stops.txt [stops-2.txt ...] stops.expanded.txt

-c = Required morphological cases (possible values: numbers 1-7, comma-separated).
        Defaults to 1,2,4 (nominative, genitive, accusative).
-m = Add previously expanded stops. Only stop name variants NOT found in the previously
        expanded file are expanded to speed up the process and preserve hand-written forms.
"""

from __future__ import unicode_literals
import autopath
import sys
import re
from collections import defaultdict
import itertools
import codecs
from ufal.morphodita import Tagger, Forms, TaggedLemmas, TokenRanges, Morpho, TaggedLemmasForms
from alex.utils.config import online_update
from alex.utils.various import remove_dups_stable
from getopt import getopt


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
    """Morphodita generator wrapper."""

    def __init__(self, morpho_model):
        self.__morpho = Morpho.load(morpho_model)
        self.__out_buf = TaggedLemmasForms()

    def generate(self, lemma, tag_wildcard, capitalized=None):
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


class ExpandStops(object):
    """This handles inflecting stop names into all desired cases in Czech."""

    def __init__(self, cases_list):
        """Initialize the expander object, initialize the morphological analyzer and generator.

        @param cases_list: List of cases (given as strings) to be used for generation \
                (Czech numbers 1-7 are used)
        """
        self.stops = defaultdict(list)
        self.cases_list = cases_list
        analyzer_model = online_update('applications/PublicTransportInfoCS/data/czech.tagger')
        generator_model = online_update('applications/PublicTransportInfoCS/data/czech.dict')
        self.__analyzer = Analyzer(analyzer_model)
        self.__generator = Generator(generator_model)

    def save(self, fname):
        """Save all stops currently held in memory to a file."""
        with codecs.open(fname, 'w', 'UTF-8') as f_out:
            for stop_name in sorted(self.stops.keys()):
                f_out.write('; '.join(self.stops[stop_name]))
                f_out.write("\n")

    def load_file(self, fname):
        """Just load a list of stops from a file and store it in memory."""
        with codecs.open(fname, 'r', 'UTF-8') as f_in:
            for line in f_in:
                variants = [var.strip() for var in line.split(';')]
                self.stops[variants[0]] = list(remove_dups_stable(variants + self.stops[variants[0]]))

    def expand_file(self, fname):
        """Load a list of stops from a file and expand it."""
        with codecs.open(fname, 'r', 'UTF-8') as f_in:
            ctr = 0
            for line in f_in:
                # load variant names for a stop
                variants = [var.strip() for var in line.split(';')]
                # skip those that needn't be inflected any more
                to_inflect = [var for var in variants if not var in self.stops[variants[0]]]
                # inflect the rest
                for variant in to_inflect:
                    words = self.__analyzer.analyze(variant)
                    # in all required cases
                    for case in self.cases_list:
                        forms = []
                        prev_tag = ''
                        for word in words:
                            forms.append(self.__inflect_word(word, case, prev_tag))
                            prev_tag = word[2]
                        # use all possible combinations if there are more variants for this case
                        inflected = map(lambda var: re.sub(r' ([\.,])', r'\1', var),
                                        remove_dups_stable([' '.join(var)
                                                            for var in itertools.product(*forms)]))
                        self.stops[variants[0]] = list(remove_dups_stable(self.stops[variants[0]] +
                                                                          inflected))
                ctr += 1
                if ctr % 1000 == 0:
                    print >> sys.stderr, '.',
        print >> sys.stderr

    def __inflect_word(self, word, case, prev_tag):
        """Inflect one word in the given case (return a list of variants)."""
        form, lemma, tag = word
        # inflect each word in nominative not following a noun in nominative
        # (if current case is not nominative)
        if re.match(r'^....1', tag) and not re.match(r'^NN..1', prev_tag) and case != '1':
            # change the case in the tag, allow all variants
            new_tag = re.sub(r'^(....)1(.*).$', r'\g<1>' + case + r'\g<2>?', tag)
            # -ice: test both sg. and pl. versions
            if (form.endswith('ice') and form[0] == form[0].upper() and
                    not re.match(r'(nemocnice|ulice)', form, re.IGNORECASE)):
                new_tag = re.sub(r'^(...)S', r'\1[SP]', new_tag)
            # try inflecting, fallback to uninflected
            capitalized = form[0] == form[0].upper()
            new_forms = self.__generator.generate(lemma, new_tag, capitalized)
            return new_forms if new_forms else [form]
        else:
            return [form]


def main():
    cases = ['1', '2', '4']
    merge_file = None
    opts, files = getopt(sys.argv[1:], 'c:m:')
    for opt, arg in opts:
        if opt == '-c':
            cases = re.split('[, ]+', arg)
        elif opt == '-m':
            merge_file = arg
    if len(files) < 2:
        sys.exit(__doc__)
    in_files = files[:-1]
    out_file = files[-1]
    es = ExpandStops(cases)
    if merge_file:
        es.load_file(merge_file)
    for in_file in in_files:
        es.expand_file(in_file)
    es.save(out_file)


if __name__ == '__main__':
    main()
