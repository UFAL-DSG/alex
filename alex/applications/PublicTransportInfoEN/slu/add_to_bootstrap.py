#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A simple script for adding new utterances along with their semantics to
bootstrap.sem and bootstrap.trn.

Usage:

./add_to_bootsrap < input.tsv

The script expects input with tab-separated transcriptions + semantics (one
utterance per line). It automatically generates the dummy 'bootstrap_XXXX.wav'
identifiers and separates the transcription and semantics into two files.
"""

from __future__ import unicode_literals

import codecs
import re
import sys


BOOTSTRAP_SEM = 'bootstrap.sem'
BOOTSTRAP_TRN = 'bootstrap.trn'

def main():
    # get lowest available number
    hi = 0
    with codecs.open(BOOTSTRAP_TRN, 'r', 'UTF-8') as fh:
        for line in fh:
            line = re.sub(r'=>.*$', '', line)
            line = re.sub(r'[^0-9]', '', line)
            if not line:
                continue
            num = int(line)
            if hi < num:
                hi = num

    # add to both files
    sem_out = codecs.open(BOOTSTRAP_SEM, 'a', 'UTF-8')
    trn_out = codecs.open(BOOTSTRAP_TRN, 'a', 'UTF-8')
    stdin_utf = codecs.getreader('UTF-8')(sys.stdin)

    utt_no = hi + 1

    for line in stdin_utf:
        line = line.strip()
        if not line:
            continue
        trn, sem = line.split('\t')
        print >> trn_out, 'bootstrap_%04d.vaw => %s' % (utt_no, trn)
        print >> sem_out, 'bootstrap_%04d.vaw => %s' % (utt_no, sem)
        utt_no += 1

    sem_out.close()
    trn_out.close()


if __name__ == '__main__':
    main()