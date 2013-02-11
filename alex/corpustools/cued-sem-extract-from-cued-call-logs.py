#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os.path
import argparse
import xml.dom.minidom
import random

import __init__

from alex.utils.various import flatten, get_text_from_xml_node

"""
This program extracts CUED semantic annotations from CUED call logs into a format which can be later processed by
cued-sem2ufal-sem.py program.

It scans for 'user-transcription.norm.xml' to extract the transcriptions and the semantics.

"""


def extract_trns_sems_from_file(file, verbose):
    """Extracts transcriptions and their semantic annotation from the provided CUED call log file."""

    trns_sems = []

    # load the file
    doc = xml.dom.minidom.parse(file)
    els = doc.getElementsByTagName("userturn")

    size = 0
    for el in els:
        transcription = el.getElementsByTagName("transcription")
        cued_da = el.getElementsByTagName("semitran")
        cued_dahyp = el.getElementsByTagName("semihyp")
        asrhyp = el.getElementsByTagName("asrhyp")
        audio = el.getElementsByTagName("rec")

        if len(transcription) != 1 or len(cued_da) != 1 or len(cued_dahyp) == 0 or len(asrhyp) == 0 or len(audio) != 1:
            # skip this node, it contains multiple elements of either transcriptionm, cued_da,
            # cued_dahyp, asrhyp, or audio.
            continue

        transcription = get_text_from_xml_node(transcription[0]).lower()
        cued_da = get_text_from_xml_node(cued_da[0])
        cued_dahyp = get_text_from_xml_node(cued_dahyp[0])
        asrhyp = get_text_from_xml_node(asrhyp[0]).lower()
        audio = audio[0].getAttribute('fname').strip()

        if verbose:
            print "#1 f:", audio
            print "#2 t:", transcription, "# s:", cued_da
            print "#3 a:", asrhyp, "# s:", cued_dahyp
            print

        if cued_da:
            trns_sems.append(
                (transcription, asrhyp, cued_da, cued_dahyp, audio))

    return trns_sems


def extract_trns_sems(indir, outdir, verbose):
    trns_sems = []

    logs = glob.glob(
        os.path.join(indir, '*', '*', 'user-transcription.norm.xml'))

    logs.sort()

    for log in logs:
        if verbose:
            print 'Processing:', log

        trns_sems.append(extract_trns_sems_from_file(log, verbose))

    trns_sems = flatten(trns_sems, (list, ))

    return trns_sems


def write_trns_sem(outdir, fname, data):
    fo = open(os.path.join(outdir, fname), 'w+')
    for transcription, asrhyp, cued_da, cued_dahyp, audio in data:
        fo.write(transcription)
        fo.write(' <=> ')
        fo.write(cued_da)
        fo.write('\n')
    fo.close()


def write_asrhyp_sem(outdir, fname, data):
    fo = open(os.path.join(outdir, fname), 'w+')
    for transcription, asrhyp, cued_da, cued_dahyp, audio in data:
        fo.write(asrhyp)
        fo.write(' <=> ')
        fo.write(cued_da)
        fo.write('\n')
    fo.close()


def write_asrhyp_semhyp(outdir, fname, data):
    fo = open(os.path.join(outdir, fname), 'w+')
    for transcription, asrhyp, cued_da, cued_dahyp, audio in data:
        fo.write(asrhyp)
        fo.write(' <=> ')
        fo.write(cued_dahyp)
        fo.write('\n')
    fo.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program extracts CUED semantic annotations from CUED call logs into a format
      which can be later processed by cued-sem2ufal-sem.py program.

      Note that no normalisation of the transcription or the recognised speech is performed.
      Any normalisation of the input text should be done before the SLU component starts
      to process the input text.

      It scans for 'user-transcription.norm.xml' to extract the transcriptions and the semantics.

      """)

    parser.add_argument('--indir', action="store", default='./cued_call_logs',
                        help='an input directory with CUED call log files (default: ./cued_call_logs)')
    parser.add_argument('--outdir', action="store", default='./cued_data',
                        help='an output directory for files with audio and their transcription (default: ./cued_data)')
    parser.add_argument(
        '-v', action="store_true", default=False, dest="verbose",
        help='set verbose oputput')

    args = parser.parse_args()

    print 'Extracting semantics from the call logs'
    trns_sems = extract_trns_sems(args.indir, args.outdir, args.verbose)

    # fix the shuffling of the data
    random.seed(0)
    random.shuffle(trns_sems)

    print "Total number of semantic annotations:", len(trns_sems)

    train = trns_sems[:int(0.8 * len(trns_sems))]
    dev = trns_sems[int(0.8 * len(trns_sems)):int(0.9 * len(trns_sems))]
    test = trns_sems[int(0.9 * len(trns_sems)):]

    print 'Saving the semantics'
    write_trns_sem(args.outdir, 'caminfo-train.sem', train)
    write_asrhyp_sem(args.outdir, 'caminfo-train.asr.sem', train)
    write_asrhyp_semhyp(args.outdir, 'caminfo-train.asr.shyp.sem', train)

    write_trns_sem(args.outdir, 'caminfo-dev.sem', dev)
    write_asrhyp_sem(args.outdir, 'caminfo-dev.asr.sem', dev)
    write_asrhyp_semhyp(args.outdir, 'caminfo-dev.asr.shyp.sem', dev)

    write_trns_sem(args.outdir, 'caminfo-test.sem', test)
    write_asrhyp_sem(args.outdir, 'caminfo-test.asr.sem', test)
    write_asrhyp_semhyp(args.outdir, 'caminfo-test.asr.shyp.sem', test)
