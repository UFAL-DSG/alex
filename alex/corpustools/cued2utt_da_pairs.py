#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from collections import namedtuple
import glob
import os
import os.path
import random
import xml.dom.minidom

if __name__ == "__main__":
    import autopath

from alex.corpustools.cued import find_logs
from alex.corpustools.trsnorm import exclude, exclude_by_dict, normalise_trs
from alex.utils.various import get_text_from_xml_node

"""
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


def extract_trns_sems_from_file(fname, verbose, fields=None, normalise=True,
                                do_exclude=True, known_words=None):
    """
    Extracts transcriptions and their semantic annotation from a CUED call log
    file.

    Arguments:
        fname -- path towards the call log file
        verbose -- print lots of output?
        fields -- names of fields that should be required for the output.
            Field names are strings corresponding to the element names in the
            transcription XML format.  (default: all five of them)
        normalise -- whether to do normalisation on transcriptions
        do_exclude -- whether to exclude transcriptions not considered suitable
        known_words -- a collection of words.  If provided, transcriptions are
            excluded which contain other words.  If not provided, excluded are
            transcriptions that contain any of _excluded_characters.  What
            "excluded" means depends on whether the transcriptions are required
            by being specified in `fields'.

    Returns a list of TurnRecords.

    """

    if verbose:
        print 'Processing', fname

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
        asrhyp = get_text_from_xml_node(
            rec.asrhyp[0]).lower() if rec.asrhyp else None
        # Filter the transcription and the ASR hypothesis through normalisation
        # and excluding non-conformant utterances.
        if transcription is not None:
            if normalise:
                transcription = normalise_trs(transcription)
            if do_exclude:
                if known_words is not None:
                    trs_excluded = exclude_by_dict(transcription, known_words)
                else:
                    trs_excluded = exclude(transcription)
                if trs_excluded:
                    if verbose:
                        print 'Excluded transcription: "{trs}".'.format(
                            trs=transcription)
                    if 'transcription' in fields:
                        continue
                    transcription = None
        if asrhyp is not None:
            if normalise:
                asrhyp = normalise_trs(asrhyp)
            if do_exclude:
                if known_words is not None:
                    asr_excluded = exclude_by_dict(asrhyp, known_words)
                else:
                    asr_excluded = exclude(asrhyp)
                if asr_excluded:
                    if verbose:
                        print 'Excluded ASR hypothesis: "{asr}".'.format(
                            asr=asrhyp)
                    if 'asrhyp' in fields:
                        continue
                    asrhyp = None

        cued_da = get_text_from_xml_node(
            rec.cued_da[0]) if rec.cued_da else None
        cued_dahyp = get_text_from_xml_node(
            rec.cued_dahyp[0]) if rec.cued_dahyp else None
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


def extract_trns_sems(infname, verbose, fields=None, ignore_list_file=None,
                      do_exclude=True, normalise=True, known_words=None):
    """
    Extracts transcriptions and their semantic annotation from a directory
    containing CUED call log files.

    Arguments:
        infname -- either a directory, or a file.  In the first case, logs are
            looked for below that directory.  In the latter case, the file is
            read line by line, each line specifying a directory or a glob
            determining the call log to include.
        verbose -- print lots of output?
        fields -- names of fields that should be required for the output.
            Field names are strings corresponding to the element names in the
            transcription XML format.  (default: all five of them)
        ignore_list_file -- a file of absolute paths or globs (can be mixed)
            specifying logs that should be skipped
        normalise -- whether to do normalisation on transcriptions
        do_exclude -- whether to exclude transcriptions not considered suitable
        known_words -- a collection of words.  If provided, transcriptions are
            excluded which contain other words.  If not provided, excluded are
            transcriptions that contain any of _excluded_characters.  What
            "excluded" means depends on whether the transcriptions are required
            by being specified in `fields'.

    Returns a list of TurnRecords.

    """

    # Interpret the arguments.
    if fields is None:
        fields = ("transcription", "semitran", "semihyp", "asrhyp", "rec")

    # Find all the log files and call the worker function on them in sequel.
    log_paths = find_logs(infname, ignore_list_file=ignore_list_file)
    log_paths.sort()
    turn_recs = list()
    for log_path in log_paths:
        turn_recs.extend(extract_trns_sems_from_file(
            log_path, verbose, fields=fields, normalise=normalise,
            do_exclude=do_exclude, known_words=known_words))
    return turn_recs


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
        description="""
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
