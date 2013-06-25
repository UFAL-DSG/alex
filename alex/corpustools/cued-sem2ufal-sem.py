#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os.path
import collections
import re
import argparse

import __init__

from alex.utils.text import split_by
from alex.corpustools.cuedda import CUEDDialogueAct
from alex.corpustools.ufaldatabase import save_database

"""
This program process CUED semantic annotations and converts them into UFAL
semantic format.  A by product of the processing is a category database which
contains a list of slots, their values, and the alternative lexical
representations. Currently the alternative value lexical representation are
trivially equal to the observed slot values.

This automatically generated category database must be manually checked and
corrected for errors observed in the data.

The database also contains a list of dialogue act types observed in the data.

It scans for all 'cued_data/*.sem' files and process them.

"""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program process CUED semantic annotations and converts them into
      UFAL semantic format.  A by product of the processing is a category
      database which contains a list of slots, their values, and the
      alternative lexical representations. Currently the alternative value
      lexical representation are trivially equal to the observed slot values.

      This automatically generated category database must be manually checked
      and corrected for errors observed in the data.

      The database also contains a list of dialogue act types observed in the
      data.

      """)

    parser.add_argument('--indir', action="store", default='./cued_data',
                        help='an input directory with CUED sem files (default: ./cued_data)')
    parser.add_argument('--outdir', action="store", default='./data',
                        help='an output directory for files in UFAL semantic format (default: ./data)')
    parser.add_argument(
        '-v', action="store_true", default=False, dest="verbose",
        help='set verbose oputput')

    args = parser.parse_args()

    indir = args.indir
    outdir = args.outdir
    verbose = args.verbose

    sem_files = glob.glob(os.path.join(indir, '*.sem'))

    slots = collections.defaultdict(set)
    ufal_da_list = collections.defaultdict(list)

    for fn in sem_files:
        print 'Processing file: ' + fn
        bnfn = os.path.basename(fn)

        f = open(fn, 'r')

        da_clustered = collections.defaultdict(set)
        for line in f:
            line = line.strip()

            if verbose:
                print '-' * 120
                print 'Input:   ' + line

            text, cued_da = line.split('<=>')
            text = text.strip()
            cued_da = cued_da.strip()

            if verbose:
                print 'Text:    ' + text
                print 'DA:      ' + cued_da
                print

            da = CUEDDialogueAct(text, cued_da)
            da.parse()

            ufal_da = da.get_ufal_da()

            if verbose:
                print 'cued_da:  ' + da.get_cued_da()
                print 'ufal_da:  ' + ufal_da

            ufal_da_list[bnfn].append((da.text, da.get_ufal_da()))
            da_clustered[da.get_ufal_da()].add(da.text)

            slts = da.get_slots_and_values()
            for slt in slts:
                slots[slt].update(slts[slt])

        fo = open(os.path.join(
            outdir, os.path.basename(fn).replace('.sem', '.grp')), 'w+')
        for key in sorted(da_clustered):
            fo.write(key)
            fo.write(' <=> ')
            fo.write(str(sorted(list(da_clustered[key]))) + '\n')
        fo.close()

        dai_unique = set()
        for da in sorted(da_clustered):
            dais = split_by(da, '&', '(', ')', '"')
            for dai in dais:
                dai_unique.add(dai)

        fo = open(os.path.join(
            outdir, os.path.basename(fn).replace('.sem', '.grp.dais')), 'w+')
        for dai in sorted(dai_unique):
            fo.write(dai)
            fo.write('\n')
        fo.close()

        da_reclustered = collections.defaultdict(set)
        for key in da_clustered:
            sem_reduced = re.sub(
                r'([a-z_0-9]+)(="[a-zA-Z0-9_\'! ]+")', r'\1', key)
            da_reclustered[sem_reduced].update(da_clustered[key])

        fo = open(os.path.join(outdir, os.path.basename(fn)
                  .replace('.sem', '.grp.reduced')), 'w+')
        for key in sorted(da_reclustered):
            fo.write(key)
            fo.write(' <=> ')
            fo.write(str(sorted(list(da_reclustered[key]))) + '\n')
        fo.close()

        dai_unique = set()
        for da in sorted(da_reclustered):
            dais = split_by(da, '&', '(', ')', '"')
            for dai in dais:
                dai_unique.add(dai)

        fo = open(os.path.join(outdir, os.path.basename(
            fn).replace('.sem', '.grp.reduced.dais')), 'w+')
        for dai in sorted(dai_unique):
            fo.write(dai)
            fo.write('\n')
        fo.close()

    for fn in ufal_da_list:
        i = 0
        if 'asr' in fn:
            ext = '.asr'
        else:
            ext = '.trn'
        fo_trn = open(os.path.join(outdir, fn.replace('.sem', '.trn')), 'w+')
        fo_sem = open(os.path.join(outdir, fn), 'w+')

        for text, da in ufal_da_list[fn]:
            wav_name = ("%06d" % i) + '.wav'
            fo_trn.write(wav_name + ' => ' + text + '\n')
            fo_sem.write(wav_name + ' => ' + da + '\n')

            i += 1

        fo_trn.close()
        fo_sem.close()

    save_database(outdir, slots)
