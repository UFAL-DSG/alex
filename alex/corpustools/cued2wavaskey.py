#!/usr/bin/env python
# vim: set fileencoding=utf-8
#
# Finds CUED XML files describing calls in the directory specified, extracts
# a couple of fields from them for each turn (transcription, ASR 1-best,
# semantics transcription, SLU 1-best) and outputs them to separate files in
# the following format:
#   {wav_filename} => {field}
#
# 2013-06
# Matěj Korvas

import argparse
import os
import random

from cued2utt_da_pairs import extract_trns_sems, TurnRecord, write_data

xmlname2recname = {'transcription': 'transcription',
                   'semitran': 'cued_da',
                   'semihyp': 'cued_dahyp',
                   'asrhyp': 'asrhyp',
                   'rec': 'audio'}


if __name__ == "__main__":
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
    Finds CUED XML files describing calls in the directory specified, extracts
    a couple of fields from them for each turn (transcription, ASR 1-best,
    semantics transcription, SLU 1-best) and outputs them to separate files in
    the following format:
        {wav_filename} => {field}

    It scans for 'user-transcription.norm.xml' (or `user-transcription.xml'
    if the former is not found in the log directory) to extract the
    transcriptions and the semantics.

      """)

    arger.add_argument('-i', '--indir',
                       default='./cued_call_logs',
                       help=('an input directory with CUED call log files '
                             '(default: ./cued_call_logs)'))
    arger.add_argument('-o', '--outdir', default='./cued_data',
                       help=('an output directory for files with audio and '
                             'their transcription (default: ./cued_data)'))
    arger.add_argument('-v', '--verbose', action="store_true",
                       help='set verbose output')
    arger.add_argument('-f', '--fields', nargs='+',
                       help=('fields of the XML transcription file that '
                             'should be extracted'))
    arger.add_argument('-g', '--ignore-missing', action='store_true',
                       help=('ignore missing values for required fields'))
    args = arger.parse_args()

    print 'Extracting semantics from the call logs...'
    req_fields = list() if args.ignore_missing else args.fields
    # import ipdb; ipdb.set_trace()
    recs = extract_trns_sems(args.indir, args.verbose, fields=req_fields)
    num_turns = len(recs)

    print "Total number of annotated user turns:", num_turns

    if args.fields is None:
        fields = ("transcription", "semitran", "semihyp", "asrhyp")
    else:
        fields = args.fields

    suffixes = {'transcription': 'trs',
                'semitran': 'sem',
                'semihyp': 'shyp',
                'asrhyp': 'asr'}

    for fldname in fields:
        print 'Saving {fld}s...'.format(fld=fldname)
        outfname = 'extracted.{suf}'.format(suf=suffixes[fldname])
        write_data(args.outdir, outfname, recs,
                   '{{rec.audio}} => {{rec.{recname}}}\n'.format(
                       recname=xmlname2recname[fldname]))
    print 'Done.  Output written to "{outdir}".'.format(
        outdir=args.outdir + os.sep)
