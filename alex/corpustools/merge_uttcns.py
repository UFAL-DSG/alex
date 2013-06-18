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
import glob

INDIR = "."


def find_files(dirname):
    return glob.glob('*.uttcn')


def merge_files(fnames, outfname):
    cndict = dict()
    for fname in fnames:
        with codecs.open(fname, encoding='UTF-8') as cnfile:
            for line in cnfile:
                key, cn = line.strip().split(' => ')
                if key not in cndict or cndict[key] == 'None':
                    cndict[key] = cn
    with codecs.open(outfname, 'w', encoding='UTF-8') as outfile:
        for key, cn in sorted(cndict.viewitems()):
            outfile.write('{key} => {val}\n'.format(key=key, val=cn))

if __name__ == "__main__":
    import sys
    merge_files(find_files(INDIR), sys.argv[1])
