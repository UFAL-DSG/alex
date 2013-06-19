#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import namedtuple
import glob
import os
import os.path
import argparse
import xml.dom.minidom
import random

if __name__ == "__main__":
    import autopath

# from alex.utils.various import flatten, get_text_from_xml_node
from alex.utils.various import get_text_from_xml_node

"""\
This program extracts CUED semantic annotations from CUED call logs into
a format which can be later processed by cued-sem2ufal-sem.py program.

It scans for 'user-transcription.norm.xml' (or `user-transcription.xml' if the
former is not found in the log directory) to extract the transcriptions and the
semantics.

"""

XML_NORM_FNAME = 'user-transcription.norm.xml'
XML_PLAIN_FNAME = 'user-transcription.xml'


TurnRecord = namedtuple(
    'TurnRecord',
    ['transcription', 'cued_da', 'cued_dahyp', 'asrhyp', 'audio'])

# The following specifies the requirements on individual fields of the data
# record for a user turn.
_field_requirements = {
    'transcription': lambda rec: len(rec.transcription) == 1,
    'semitran': lambda rec: len(rec.cued_da) == 1,
    'semihyp': lambda rec: len(rec.cued_dahyp) != 0,
    'asrhyp': lambda rec: len(rec.asrhyp) != 0,
    'rec': lambda rec: len(rec.audio) == 1,
}


def _make_rec_filter(fields):
    fld_filters = tuple(_field_requirements[fld] for fld in fields)
    return lambda rec: all(fld_filter(rec) for fld_filter in fld_filters)


def extract_trns_sems_from_file(fname, verbose, fields=None):
    """\
    Extracts transcriptions and their semantic annotation from a CUED call log
    file.

    Arguments:
        fname -- path towards the call log file
        verbose -- print lots of output?
        fields -- names of fields that should be required for the output.
            Field names are strings corresponding to the element names in the
            transcription XML format.  (default: all five of them)

    Returns a list of TurnRecords.

    """

    # Interpret the arguments.
    if fields is None:
        fields = ("transcription", "semitran", "semihyp", "asrhyp", "rec")
    rec_filter = _make_rec_filter(fields)

    # Load the file.
    doc = xml.dom.minidom.parse(fname)
    els = doc.getElementsByTagName("userturn")

    trns_sems = []
    for el in els:
        rec = TurnRecord(
            transcription=el.getElementsByTagName("transcription"),
            cued_da=el.getElementsByTagName("semitran"),
            cued_dahyp=el.getElementsByTagName("semihyp"),
            asrhyp=el.getElementsByTagName("asrhyp"),
            audio=el.getElementsByTagName("rec")
        )

        if not rec_filter(rec):
            # Skip this node, it contains a wrong number of elements of either
            # transcription, cued_da, cued_dahyp, asrhyp, or audio.
            continue

        # XXX Here we take always the first tag having the respective tag name.
        transcription = get_text_from_xml_node(
            rec.transcription[0]).lower() if rec.transcription else None
        cued_da = get_text_from_xml_node(
            rec.cued_da[0]) if rec.cued_da else None
        cued_dahyp = get_text_from_xml_node(
            rec.cued_dahyp[0]) if rec.cued_dahyp else None
        asrhyp = get_text_from_xml_node(
            rec.asrhyp[0]).lower() if rec.asrhyp else None
        audio = rec.audio[0].getAttribute(
            'fname').strip() if rec.audio else None
        rec = TurnRecord(transcription, cued_da, cued_dahyp, asrhyp, audio)

        if verbose:
            print "#1 f:", rec.audio
            print "#2 t:", rec.transcription, "# s:", rec.cued_da
            print "#3 a:", rec.asrhyp, "# s:", rec.cued_dahyp
            print

        if rec.cued_da or 'semitran' not in fields:
            trns_sems.append(rec)

    return trns_sems


def extract_trns_sems(indir, verbose, fields=None):
    """\
    Extracts transcriptions and their semantic annotation from a directory
    containing CUED call log files.

    Arguments:
        indir -- path towards the CUED call logs directory
        verbose -- print lots of output?
        fields -- names of fields that should be required for the output.
            Field names are strings corresponding to the element names in the
            transcription XML format.  (default: all five of them)

    Returns a list of TurnRecords.

    """

    # Interpret the arguments.
    if fields is None:
        fields = ("transcription", "semitran", "semihyp", "asrhyp", "rec")

    trns_sems = list()
    # Find all the log files below `indir'.
    # log_fnames = sorted(glob.glob(
        # os.path.join(indir, '*', '*', 'user-transcription.norm.xml')))
    log_dirnames = sorted(filter(os.path.isdir,
        glob.iglob(os.path.join(indir, '*', '*'))))
    log_fnames = list()
    for log_dirname in log_dirnames:
        dir_fnames = os.listdir(log_dirname)
        if XML_NORM_FNAME in dir_fnames:
            log_fnames.append(os.path.join(log_dirname, XML_NORM_FNAME))
        elif XML_PLAIN_FNAME in dir_fnames:
            log_fnames.append(os.path.join(log_dirname, XML_PLAIN_FNAME))

    for log_fname in log_fnames:
        if verbose:
            print 'Processing', log_fname

        trns_sems.extend(
            extract_trns_sems_from_file(log_fname, verbose, fields=fields))
    # XXX The following commented out by MK together with replacing "append" by
    # "extend" in the line above.
    # trns_sems = flatten(trns_sems, (list, ))

    return trns_sems


def write_data(outdir, fname, data, tpt):
    # TODO Document.
    with open(os.path.join(outdir, fname), 'w') as outfile:
        for rec in data:
            outfile.write(tpt.format(rec=rec))


def write_trns_sem(outdir, fname, data):
    write_data(outdir, fname, data, '{rec.transcription} <=> {rec.cued_da}\n')


def write_asrhyp_sem(outdir, fname, data):
    write_data(outdir, fname, data, '{rec.asrhyp} <=> {rec.cued_da}\n')


def write_asrhyp_semhyp(outdir, fname, data):
    write_data(outdir, fname, data, '{rec.asrhyp} <=> {rec.cued_dahyp}\n')


if __name__ == '__main__':
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
    This program extracts CUED semantic annotations from CUED call logs into
    a format which can be later processed by the `cued-sem2ufal-sem.py' program.

    Note that no normalisation of the transcription or the recognised speech
    is performed.  Any normalisation of the input text should be done before
    the SLU component starts to process the input text.

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
    args = arger.parse_args()

    print 'Extracting semantics from the call logs...'
    trns_sems = extract_trns_sems(args.indir, args.verbose, fields=args.fields)
    num_turns = len(trns_sems)

    # Fix shuffling of the data.
    random.seed(0)
    random.shuffle(trns_sems)

    print "Total number of annotated user turns:", num_turns

    annion_parts = {
        'train': trns_sems[:int(0.8 * num_turns)],
        'dev': trns_sems[int(0.8 * num_turns):int(0.9 * num_turns)],
        'test': trns_sems[int(0.9 * num_turns):]}

    if args.fields is None:
        fields = ("transcription", "semitran", "semihyp", "asrhyp", "rec")
    else:
        fields = args.fields

    if 'transcription' in fields and 'semitran' in fields:
        print 'Saving gold transcriptions, gold semantics...'
        for part_name, part in annion_parts.iteritems():
            write_trns_sem(args.outdir,
                           'caminfo-{part}.sem'.format(part=part_name),
                           part)
    if 'asrhyp' in fields and 'semitran' in fields:
        print 'Saving ASR transcriptions, gold semantics...'
        for part_name, part in annion_parts.iteritems():
            write_asrhyp_sem(args.outdir,
                             'caminfo-{part}.asr.sem'.format(part=part_name),
                             part)
    if 'asrhyp' in fields and 'semihyp' in fields:
        print 'Saving ASR transcriptions, SLU semantics...'
        for part_name, part in annion_parts.iteritems():
            write_asrhyp_semhyp(
                args.outdir,
                'caminfo-{part}.asr.shyp.sem'.format(part=part_name),
                part)
    print 'Done.  Output written to "{outdir}".'.format(outdir=args.outdir)
