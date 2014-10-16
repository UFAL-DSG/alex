#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
from collections import defaultdict

from components.nlg.tools.en import every_word_for_number


prefixes = {
    'st':'saint',
    'st.': 'saint',
    'e': 'east',
    'w': 'west',
    'n': 'north',
    's': 'south',
    }

suffixes = {
    'av': 'avenue',
    'avs': 'avenues',
    'bl': 'boulevard',
    'blvd': 'boulevard',
    'ctr': 'center',
    'dr': 'drive',
    'ft' : 'fort',
    'hts': 'heights',
    'jct':'junction',
    'mt': 'mount',
    'n' : 'north',
    'opp': 'opp',
    'pk': 'park',
    'pkwy': 'parkway',
    'py': 'parkway',
    'pl': 'place',
    'rd': 'road',
    'rdwy': 'roadway',
    'rdy': 'roadway',
    'st': 'street',
    'sts': 'streets',
    'sq': 'square',
    'tpke': 'turnpike',
    '#' : 'number ',

}


def spell_if_number(word, use_coupling, ordinal=True):
    if word.isdigit():
        return every_word_for_number(int(word), ordinal, use_coupling)
    else:
        return word


def expand(stop):
    words = stop.lower().split()

    words[0] = prefixes.get(words[0], words[0])
    words[0] = spell_if_number(words[0], True)
    words = [suffixes.get(w, w) for w in words]
    words = [spell_if_number(w, True, True) for w in words]

    return " ".join(words).lower()


def get_column_index(header, caption, default):
    for i, h in enumerate(header.split(',')):
        if h == caption:
            return i
    return default


def hack_stops(stops):
    extras = []
    for stop in stops:
        # make 'hundred'/'one hundred' variants
        if "hundred" in stop:
            extras.append(stop.replace("hundred", "one hundred"))
        # apostroph is mandatory
        if "'s" in stop:
            extras.append(stop.replace("'s", "s"))
    stops.extend(extras)


def expand_stops(file_name):
    stops = defaultdict(list)
    with codecs.open(file_name, 'r', 'UTF-8') as stopsFile:
        header = stopsFile.readline()

        stop_index = get_column_index(header, "stop_name", 2)

        for line in stopsFile:
            reversed = True;
            if line.startswith('#') or not line:  # skip comments
                continue

            fields = line.strip().split(',')
            stop = fields[stop_index].strip('"');

            conjunctions = [' and ', ' on ']

            if '-' in stop:
                elements = stop.split('-');
            elif '(' in stop:
                elements = stop.replace(')', '').split('(')
                reversed = False;
                # lexington av/63 street
            elif '/' in stop:
                elements = stop.split('/')
                # cathedral pkwy (110 st)
            elif '&' in stop:
                elements = stop.split('&')
                # BARUCH INFORMATION & TECH BLDG
            else:
                elements = [stop, ]

            expansion = [expand(el) for el in elements]
            # print(expansion)


            stops[stop] = [" ".join(expansion), ]
            if len(expansion) > 1:
                for conjunction in conjunctions:
                    stops[stop].append(conjunction.join(expansion))
                if reversed:
                    stops[stop].append(" ".join(expansion[::-1]))

            hack_stops(stops[stop])
    return stops


def main():
    # transport_dir = "/home/m2rtin/Desktop/transport/";
    # files_to_expand = [file for file in listdir(transport_dir)]
    files_to_expand = [
        '/home/m2rtin/Desktop/transport/bus_staten_island.txt',
        '/home/m2rtin/Desktop/transport/bus_bronx.txt',
        '/home/m2rtin/Desktop/transport/bus_brooklyn.txt',
        '/home/m2rtin/Desktop/transport/bus_company.txt',
        '/home/m2rtin/Desktop/transport/bus_manhattan.txt',
        '/home/m2rtin/Desktop/transport/bus_queens.txt',
        '/home/m2rtin/Desktop/transport/ferry_ny_waterway.txt',
        '/home/m2rtin/Desktop/transport/ferry_staten_island.txt',
        '/home/m2rtin/Desktop/transport/metro_stops.txt',
        "/home/m2rtin/Desktop/transport/attractions.txt",
        ]

    file_out = "/home/m2rtin/alex/alex/applications/PublicTransportInfoEN/data/_expanded_stops.txt"

    with codecs.open(file_out, 'w', 'UTF-8') as output:
        for file in files_to_expand:
            print >> output, '#-' + file
            expansion = expand_stops(file)
            for key in expansion:
                print >> output, key + '\t' + "; ".join(expansion[key])


if __name__ == '__main__':
    main()

#todo: stops_cities.tsv -> New York\t_station_, New York

# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
#
# """
# Expanding Czech stop/city names with inflection forms in all given morphological cases.
#
# Usage:
#
# ./expand_stops.py [-l] [-p] [-m previous.expanded.txt] stops.txt [stops-2.txt ...] stops.expanded.txt
#
# -m = Add previously expanded stops. Only stop name variants NOT found in the previously
#         expanded file are expanded to speed up the process and preserve hand-written forms.
# -p = Strip punctuation off surface forms
# -l = Lowercase surface forms
# """
#
# from __future__ import unicode_literals
# import autopath
# import sys
# import re
# from collections import defaultdict
# import itertools
# import codecs
# from ufal.morphodita import Tagger, Forms, TaggedLemmas, TokenRanges, Morpho, TaggedLemmasForms
# from alex.utils.config import online_update
# from alex.utils.various import remove_dups_stable
# from getopt import getopt
#
#
# class ExpandStops(object):
#     """This handles inflecting stop names into all desired cases in Czech."""
#
#     def __init__(self, strip_punct, lowercase_forms):
#
#         self.stops = defaultdict(list)
#         # initialize postprocessing
#         postprocess_func = ((lambda text: re.sub(r' ([\.,])', r'\1', text))
#                             if not strip_punct
#                             else (lambda text: re.sub(r' [\.,\-–\(\)\{\}\[\];\\\/+&](?: [\.,\-–\(\)\{\}\[\];])*( |$)', r'\1', text)))
#         if lowercase_forms:
#             lc_func = lambda text: postprocess_func(text).lower()
#             self.__postprocess_func = lc_func
#         else:
#             self.__postprocess_func = postprocess_func
#
#     def save(self, fname):
#         """Save all stops currently held in memory to a file."""
#         with codecs.open(fname, 'w', 'UTF-8') as f_out:
#             for stop_name in sorted(self.stops.keys()):
#                 f_out.write(stop_name + "\t")
#                 f_out.write('; '.join(self.stops[stop_name]))
#                 f_out.write("\n")
#
#     def parse_line(self, line):
#         """Load one line from the input file (tab-separated main form or
#         implicit main form supported)."""
#         if '\t' not in line:
#             stop = None
#             variants = line
#         else:
#             stop, variants = line.split('\t')
#         variants = [var.strip() for var in variants.split(';')]
#         if stop is None:
#             stop = variants[0]
#         return stop, variants
#
#     def load_file(self, fname):
#         """Just load a list of stops from a file and store it in memory."""
#         with codecs.open(fname, 'r', 'UTF-8') as f_in:
#             for line in f_in:
#                 if line.startswith('#'):  # skip comments
#                     continue
#                 stop, variants = self.parse_line(line)
#                 self.stops[stop] = list(remove_dups_stable(variants + self.stops[stop]))
#
#     def expand_file(self, fname):
#         """Load a list of stops from a file and expand it."""
#         with codecs.open(fname, 'r', 'UTF-8') as f_in:
#             ctr = 0
#             for line in f_in:
#                 if line.startswith('#'):  # skip comments
#                     continue
#                 # load variant names for a stop
#                 stop, variants = self.parse_line(line)
#                 # skip those that needn't be inflected any more
#                 to_inflect = [var for var in variants if not var in self.stops[stop]]
#                 # inflect the rest
#                 for variant in to_inflect:
#                     words = self.__analyzer.analyze(variant)
#                     # in all required cases
#                     for case in self.cases_list:
#                         forms = []
#                         prev_tag = ''
#                         for word in words:
#                             forms.append(self.__inflect_word(word, case, prev_tag))
#                             prev_tag = word[2]
#                         # use all possible combinations if there are more variants for this case
#                         inflected = map(self.__postprocess_func,
#                                         remove_dups_stable([' '.join(var)
#                                                             for var in itertools.product(*forms)]))
#                         self.stops[stop] = list(remove_dups_stable(self.stops[stop] + inflected))
#                 ctr += 1
#                 if ctr % 1000 == 0:
#                     print >> sys.stderr, '.',
#         print >> sys.stderr
#
#     def __inflect_word(self, word, case, prev_tag):
#         """Inflect one word in the given case (return a list of variants)."""
#         form, lemma, tag = word
#         # inflect each word in nominative not following a noun in nominative
#         # (if current case is not nominative), avoid numbers
#         if (re.match(r'^[^C]...1', tag) and
#             not re.match(r'^NN..1', prev_tag) and
#             not form in ['římská'] and
#             case != '1'):
#             # change the case in the tag, allow all variants
#             new_tag = re.sub(r'^(....)1(.*).$', r'\g<1>' + case + r'\g<2>?', tag)
#             # -ice: test both sg. and pl. versions
#             if (form.endswith('ice') and form[0] == form[0].upper() and
#                     not re.match(r'(nemocnice|ulice|vrátnice)', form, re.IGNORECASE)):
#                 new_tag = re.sub(r'^(...)S', r'\1[SP]', new_tag)
#             # try inflecting, fallback to uninflected
#             capitalized = form[0] == form[0].upper()
#             new_forms = self.__generator.generate(lemma, new_tag, capitalized)
#             return new_forms if new_forms else [form]
#         else:
#             return [form]
#
#
# def main():
#     merge_file = None
#     strip_punct = False
#     lowercase_forms = False
#     opts, files = getopt(sys.argv[1:], 'm:pl')
#     for opt, arg in opts:
#         if opt == '-m':
#             merge_file = arg
#         elif opt == '-p':
#             strip_punct = True
#         elif opt == '-l':
#             lowercase_forms = True
#     if len(files) < 2:
#         sys.exit(__doc__)
#     in_files = files[:-1]
#     out_file = files[-1]
#     es = ExpandStops(strip_punct, lowercase_forms)
#     if merge_file:
#         es.load_file(merge_file)
#     for in_file in in_files:
#         es.expand_file(in_file)
#     es.save(out_file)
#
#
# if __name__ == '__main__':
#     main()
