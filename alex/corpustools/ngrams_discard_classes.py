#!/usr/bin/env python
# encoding: utf-8
# Copyright (c) 2015, Ondrej Platek, Ufal MFF UK <oplatek@ufal.mff.cuni.cz>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
# WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
# MERCHANTABLITY OR NON-INFRINGEMENT.
# See the Apache 2 License for the specific language governing permissions and
# limitations under the License.
import codecs
from collections import defaultdict


def class_prob_file2dict(filename):
    d = defaultdict(dict)
    with codecs.open(filename, 'r', 'utf-8') as r:
        for line in r:
           cls_name, prob, word = line.strip().split(' ', 2)
           d[cls_name][word] = float(prob)
    return d


def gen_sublist(l, n):
    res = []
    for i in range(len(l) - n + 1):
        res.append(l[i:i+n])
    return res


def expand_ngram(words, count, ngram_order, cls_dict, force_ints, class_smooth):
    expws = [[]]
    for w in words:
        if w in cls_dict:
            last_w_alt = cls_dict[w]
            for last_w, prob in last_w_alt.iteritems():
                for expw in expws:
                    expw.append((last_w, prob))
        else:
            for expw in expws:
                expw.append((w, 1.0))
    expanded_ngrams = []
    for expw in expws:
        ws = [w for w, _ in expw]
        coef = sum([c for _, c in expw])
        if class_smooth > 0:
            coef += class_smooth
        if len(ws) > ngram_order:
            for sub in gen_sublist(ws, ngram_order):
                expanded_ngrams.append((sub, coef)) 
        else:
            expanded_ngrams.append((ws, coef))
    if force_ints:
        pass  # TODO I do not to need to use it if I won't be using fractional counts in the first place in replace_with_classes
    return expanded_ngrams


def main(ngram_file, ngram_order, class_file, out_ngram_no_classes, 
        force_integer_counts=False,
        class_smooth=0,
        skip_first_lines=1,
        ):
    cls_dict = class_prob_file2dict(class_file)
    wrt_string = '%s %d\n' if force_integer_counts else '%s %f\n'
    with codecs.open(ngram_file, 'r', 'utf-8') as r:
        with codecs.open(out_ngram_no_classes, 'w', 'utf-8') as w:
            for i, line in enumerate(r):
                if i < skip_first_lines:
                    continue
                line_arr = line.strip().split()
                ngram, count = line_arr[:-1], float(line_arr[-1])
                ex = expand_ngram(ngram, count, ngram_order, cls_dict, 
                    force_integer_counts, class_smooth)
                for ws, c in ex:
                    w.write(wrt_string % (' '.join(ws), c))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Expand all class labels in ngrams file with class members.""")
    parser.add_argument('input_file')
    parser.add_argument('ngram_order', type=int)
    parser.add_argument('class_file')
    parser.add_argument('output_file')
    parser.add_argument('-i', '--force-interger-counts', default=False, action='store_true',
        help="""When expanding the class labels to its instances its done in proportion
        of the instance occurance in the class.
        Naturally, fractional counts emerges if discounting is used amoung class members.
        This option force the counts to be integers again""")
    parser.add_argument('-c', '--add-n-smoothing-for-classes', type=int, default=0)
    args = parser.parse_args()
    main(parser.input_file, parser.ngram_order, parser.class_file, 
            parser.output_file, force_integer_counts=parser.force_integer_counts,
            class_smooth=parser.add_n_smoothing_for_classes)
