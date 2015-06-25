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
"""
TODO better string matching of class ngrams - now - O(n*n) * |input_file|
"""
from __future__ import unicode_literals, division
import argparse
from collections import defaultdict
import codecs
import random


def classfile2dict(filename, add_n_smoothing):
    d = defaultdict(dict)
    with codecs.open(filename, 'r', 'utf-8') as r:
        for line in r:
           cls_name, word = line.strip().split(' ', 1)
           d[word][cls_name] = add_n_smoothing
    return d


def estimate_counts(input_file, counts):
    with codecs.open(input_file, 'r', 'utf-8') as r:
        for line in r:
            line = line.strip().split()
            i = 0
            while i < len(line):
                replaced = False
                # TODO too bad complexity O(n*n) - all n-grams
                for n in reversed(range(1, len(line) - i + 1)):
                    ngram = ' '.join(line[i:i+n])
                    if not ngram in counts:
                        continue
                    else:
                        ngram_classes = counts[ngram]
                        assert(len(ngram_classes) > 0)
                        # ngram may belong to more classes - choose stochasticly
                        cls = random.sample(ngram_classes, 1)[0]
                        counts[ngram][cls] += 1
                        i += n  # continue after ngram
                        replaced = True
                        break
                if not replaced:
                    i += 1 # try next starting position
    return counts


def normalize(class_counts):
    for d in class_counts.itervalues():
        total = sum(d.itervalues())
        for k in d:
            d[k] /= total


def counts2file(class_counts, filename):
    with codecs.open(filename, 'w', 'utf-8') as w:
        for cls_name, d in sorted(class_counts.iteritems()):
            for words, probs in sorted(d.iteritems()):
                w.write('%s %f %s\n' % (cls_name, probs, words))  # TODO 3.99343e-05 cannot be printed


def replace_with_classes(input_file, counts, output_file):
    with codecs.open(input_file, 'r', 'utf-8') as r:
        with codecs.open(output_file, 'w', 'utf-8') as w:
            for line in r:
                line = line.strip().split()
                new_line, i = [], 0
                while i < len(line):
                    replaced = False
                    # TODO too bad complexity O(n*n) - all n-grams
                    for n in reversed(range(len(line) - i + 1)):
                        n += 1
                        ngram = ' '.join(line[i:i+n])
                        if not ngram in counts:
                            continue
                        else:
                            ngram_classes = counts[ngram]
                            assert(len(ngram_classes) > 0)
                            # ngram may belong to more classes - choose stochasticly TODO
                            cls = random.sample(ngram_classes, 1)[0]
                            new_line.append(cls)
                            i += n  # continue after ngram
                            replaced = True
                            break
                    if not replaced:
                        new_line.append(line[i])
                        i += 1 # try next starting position
                w.write(' '.join(new_line))
                w.write('\n')


def main(input_file, class_file, class_count_file, output_file, add_n_smoothing=1, counts_only=False):
    basic_counts = classfile2dict(class_file, add_n_smoothing)
    word_counts = estimate_counts(input_file, basic_counts)
    class_counts = defaultdict(dict)
    for w, class_dict in word_counts.iteritems():
        for cls, count in class_dict.iteritems():
            class_counts[cls][w] = count
    if not counts_only:
        normalize(class_counts)
    counts2file(class_counts, class_count_file)
    replace_with_classes(input_file, word_counts, output_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Replace all instances of class with class label.""")
    parser.add_argument('input_file')
    parser.add_argument('class_file')
    parser.add_argument('class_count_file', help='Estimate probabilities among class members based on input file')
    parser.add_argument('output_file')
    parser.add_argument('-s', '--add-n-smoothing', default=1, type=int, help='Applies smoothing among class members.')
    parser.add_argument('-c', '--counts-only', default=False, action='store_true', help='Do not use the default normalization to probabilities and compute counts only for class count file')
    args = parser.parse_args()
    main(args.input_file, args.class_file, args.class_count_file,
            args.output_file, add_n_smoothing=args.add_n_smoothing, counts_only=args.counts_only)
