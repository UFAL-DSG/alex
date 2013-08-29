#!/usr/bin/env python
# vim: set fileencoding=utf-8
#
# Transforms a LM stored in the ARPA format into a word network for HTK that
# retains unigram probabilities.

from __future__ import unicode_literals

__author__ = "Matěj Korvas"
__date__ = "2013-08-29"


import codecs
import math
import re

ngrams_rx = re.compile('^\\\\(\\d+)-grams:$')
LOG10 = math.log(10)


def parse_lprob(instr):
    """
    Transforms a logprob string from ARPA to a logprob float suitable for HTK.
    """
    return LOG10 * float(instr)


def read_arpa(infname):
    """
    Reads an LM stored in the ARPA format.

    This method has never been used, use at your own risk!

    Arguments:
        infname -- path towards the ARPA file

    Returns a list of mappings {n-gram -> [logprob, ?backoff-logprob]} indexed
    with n, length of the n-gram. The second member of the list,
    backoff-logprob, is included whenever it was specified in the ARPA file.

    """
    ngrams = [None]  # :: [n -> {ngram -> [lprob, ?backoff-lprob]}]
    with codecs.open(infname, encoding='UTF-8') as infile:
        n = None
        for line in infile:
            line = line.rstrip()
            # Process the special '\<int>-grams:' lines.
            if line.endswith('-grams:'):
                match = ngrams_rx.match(line)
                if match is not None:
                    n = int(match.group(1))
                    ngrams.extend(dict() for _ in xrange(n - len(ngrams) + 1))

            # Process the typical n-gram-listing lines.
            if line and n:
                parts = line.split()
                if len(parts) == n + 1:
                    ngrams[n][' '.join(parts[1:])] = [parse_lprob(parts[0])]
                elif len(parts) == n + 2:
                    ngrams[n][' '.join(parts[1:-1])] = [parse_lprob(parts[0]),
                                                        parse_lprob(parts[-1])]
    return ngrams


def read_arpa_unigrams(infname):
    """
    Reads the mapping {unigram -> logprob} from a LM stored in the ARPA format.

    Arguments:
        infname -- path towards the ARPA file

    """
    unigrams = dict()  # :: {word -> lprob}
    with codecs.open(infname, encoding='UTF-8') as infile:
        # Find the '\\1-grams:' line.
        for line in infile:
            if line == '\\1-grams:\n':
                break
        else:
            return unigrams
        # Read all the unigrams.
        for line in infile:
            parts = line.split()
            if not parts:
                break
            unigrams[parts[1]] = parse_lprob(parts[0])
    return unigrams


def write_wdnet_unigrams(outfname, unigrams):
    """
    Writes a HTK word network file capturing a word loop with unigram
    probabilities assigned.

    Arguments:
        outfname -- path towards the HTK word net file
        unigrams -- mapping {unigram -> logprob of the unigram} (where the log
            is understood to be a natural logarithm -- basis e)

    """

    n_words = len(unigrams)
    n_nodes = n_words + 4  # we will add 4 '!NULL' nodes
    n_edges = 2 * n_words + 3

    with codecs.open(outfname, 'w', encoding='UTF-8') as outfile:
        # Write the header.
        outfile.write('VERSION=1.0\n')
        outfile.write('N={N} L={L}\n'.format(N=n_nodes, L=n_edges))
        # Write the nodes.
        outfile.write('I=0 W=!NULL\nI=1 W=!NULL\n')
        idx2word = [None, None]
        for index, word in enumerate(sorted(unigrams), start=2):
            idx2word.append(word)
            outfile.write('I={idx} W={word}\n'.format(idx=index, word=word))
        outfile.write('I={prelast} W=!NULL\nI={last} W=!NULL\n'
                      .format(prelast=n_nodes - 2, last=n_nodes - 1))
        # Write the edges.
        # -- Write the first edges.
        outfile.write('J=0 S=0 E=1 l=0.00\n')
        outfile.write('J=1 S={prelast} E=1 l=0.00\n'
                      .format(prelast=n_nodes - 2))
        # -- Write the edges start - node.
        edge_idx = 2
        for node_idx in xrange(2, n_nodes - 2):
            outfile.write('J={eidx} S=1 E={nidx} l={lik}\n'
                          .format(eidx=edge_idx, nidx=node_idx,
                                  lik=unigrams[idx2word[node_idx]]))
            edge_idx += 1
        # -- Write the edges node - end.
        for node_idx in xrange(2, n_nodes - 2):
            outfile.write('J={eidx} S={nidx} E={prelast} l=0.00\n'
                          .format(eidx=edge_idx,
                                  nidx=node_idx,
                                  prelast=n_nodes - 2))
            edge_idx += 1
        # -- Write the last edge.
        outfile.write('J={L} S={prelast} E={last} l=0.00\n'
                      .format(L=n_edges - 1,
                              prelast=n_nodes - 2,
                              last=n_nodes - 1))


def main(infname, outfname):
    """
    Transforms a LM stored in the ARPA format into a word network for HTK that
    retains unigram probabilities.

    Arguments:
        infname -- path towards the input ARPA file
        outfname -- path towards the output HTK word net file
    """
    write_wdnet_unigrams(outfname, read_arpa_unigrams(infname))


if __name__ == "__main__":
    import argparse

    arger = argparse.ArgumentParser(
        description="Transforms a LM stored in the ARPA format into a word "
        "network for HTK that retains unigram probabilities.")
    arger.add_argument('arpa_fname', metavar='INFILE',
                       help="Path towards the input ARPA file.")
    arger.add_argument('wdnet_fname', metavar='OUTFILE',
                       help="Path towards the output HTK word net file.")
    args = arger.parse_args()
    main(args.arpa_fname, args.wdnet_fname)
