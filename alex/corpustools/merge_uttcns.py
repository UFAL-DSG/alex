#!/usr/bin/env python
# vim: set fileencoding=utf-8
#
# Merges ASR-decoded confusion networks from several files produced by
# multiple runs of the script `get_jasr_confnets.py' into one file.
#
# 2013-06
# Matěj Korvas

from __future__ import unicode_literals

import codecs
from collections import Counter
import glob

INDIR = "."


def find_files(dirname):
    return glob.glob('*.uttcn')


def find_best_cn(cns):
    """Determines which one of decoded confnets seems the best."""
    non_none_cns = [cn for cn in cns if cn != 'None']
    if non_none_cns:
        # Restrict the choice to those confnets that occur most often.
        counts = Counter(non_none_cns)
        most_common, highest_count = counts.most_common(1)
        non_none_cns = [cn for (cn, count) in counts.iteritems()
                        if count == highest_count]
        # Choose the longest confnet (measured by its representation).
        return max((len(cn), cn) for cn in non_none_cns)[1]
    else:
        return 'None'


def merge_files(fnames, outfname):
    cndict = dict()
    for fname in fnames:
        with codecs.open(fname, encoding='UTF-8') as cnfile:
            for line in cnfile:
                key, cn = line.strip().split(' => ')
                cndict.setdefault(key, list()).append(cn)
    with codecs.open(outfname, 'w', encoding='UTF-8') as outfile:
        for key, cns in sorted(cndict.viewitems()):
            if len(cns) > 1:
                best_cn = find_best_cn(cns)
            else:
                best_cn = cn[0]
            outfile.write('{key} => {val}\n'.format(key=key, val=best_cn))

if __name__ == "__main__":
    import sys
    merge_files(find_files(INDIR), sys.argv[1])
