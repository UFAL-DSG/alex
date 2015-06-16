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
from __future__ import unicode_literals, division
import codecs
from collections import defaultdict
from itertools import izip
from functools import reduce
import operator


def class_prob_file2dict(filename):
    d = defaultdict(dict)
    with codecs.open(filename, 'r', 'utf-8') as r:
        for line in r:
           cls_name, prob, word = line.strip().split(' ', 2)
           d[cls_name][word] = float(prob)
    return d


def gen_sublist(l, n):
    '''TODO Generator of substrings of length n.
    Assuming input strings & output strings.'''
    res = []
    for i in range(len(l) - n + 1):
        res.append(l[i:i+n])
    return res


def expand_classes(list_of_list_of_tuples):
    """TODO Generator of tuples from [cl1, cl2, cl3]"""
    if len(list_of_list_of_tuples) == 0:
        yield (), 1.0
    else:
        indexes = [0] * len(list_of_list_of_tuples)
        num_items = [len(d) for d in list_of_list_of_tuples]
        assert all([n > 0 for n in num_items])
        finished = False
        while not finished:
            class_prob_pairs = [klist[i] for klist, i in izip(list_of_list_of_tuples, indexes)]
            t = tuple([c for c, _ in class_prob_pairs])
            coef = sum([c for _, c in class_prob_pairs])
            yield t, coef
            indexes[0] += 1
            overflow_check, i = True, 0
            while overflow_check:
                if indexes[i] == num_items[i]:
                    if i == len(indexes) - 1:
                        assert(indexes[-1] == num_items[-1])
                        finished = True
                        break
                    indexes[i], indexes[i + 1], i = 0, indexes[i + 1] + 1, i + 1
                else:
                    overflow_check = False


def expand_ngram(words, count, ngram_order, cls_dict, force_ints, class_smooth, output):
    # TODO compute in advance the number of candidates and limit it to something reasonable
    # TODO prune the low probably ngrams - DO NOT even generate them
    wrt_string = '%s %d\n' if force_ints else '%s %f\n'
    classes_in_words = [cls_dict[w].items() for w in words if w in cls_dict]  # TODO change na iteritems
    classes_size = [len(c) for c in classes_in_words]
    num_alternative = count * reduce(operator.mul, classes_size , 1)
    min_count = (count / num_alternative) + class_smooth

    template = ' '.join(['%s' if w in cls_dict else w for w in words])  # usage: template % tuple([cl1, cl2, cl3, ..])
    for expanded_tuple, prob in expand_classes(classes_in_words):
        exp_ngram = template % expanded_tuple
        exp_ngram = exp_ngram.split()
        if class_smooth > 0:
            prob += class_smooth
        if len(exp_ngram) > ngram_order:
            for sub in gen_sublist(exp_ngram, ngram_order):
                output.write(wrt_string % (' '.join(sub), prob))
        else:
            output.write(wrt_string % (' '.join(exp_ngram), prob))


def main(ngram_file, ngram_order, class_file, out_ngram_no_classes,
        force_integer_counts=False,
        class_smooth=0,
        skip_first_lines=2,
        ):
    cls_dict = class_prob_file2dict(class_file)
    with codecs.open(ngram_file, 'r', 'utf-8') as r:
        with codecs.open(out_ngram_no_classes, 'w', 'utf-8') as w:
            for i, line in enumerate(r):
                if i < skip_first_lines:
                    continue
                line_arr = line.strip().split()
                ngram, count = line_arr[:-1], float(line_arr[-1])
                # import ipdb; ipdb.set_trace()
                ex = expand_ngram(ngram, count, ngram_order, cls_dict,
                    force_integer_counts, class_smooth, w)


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
