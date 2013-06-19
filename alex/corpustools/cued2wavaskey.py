#!/usr/bin/env python
# vim: set fileencoding=utf-8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
Finds CUED XML files describing calls in the directory specified, extracts
a couple of fields from them for each turn (transcription, ASR 1-best,
semantics transcription, SLU 1-best) and outputs them to separate files in
the following format:
  {wav_filename} => {field}

An example ignore list file could contain the following three lines:

/some-path/call-logs/log_dir/some_id.wav
some_id.wav
jurcic-??[13579]*.wav

The first one is an example of an ignored path. On UNIX, it has to start with
a slash. On other platforms, an analogic convention has to be used.

The second one is an example of a literal glob.

The last one is an example of a more advanced glob. It says basically that
all odd dialogue turns should be ignored.

"""

# 2013-06
# Matěj Korvas

import argparse
import os
import os.path

if __name__ == "__main__":
    import autopath

from alex.corpustools.cued2utt_da_pairs import extract_trns_sems, write_data


_xmlname2recname = {'transcription': 'transcription',
                    'semitran': 'cued_da',
                    'semihyp': 'cued_dahyp',
                    'asrhyp': 'asrhyp',
                    'rec': 'audio'}
_suffixes = {'transcription': 'trs',
             'semitran': 'sem',
             'semihyp': 'shyp',
             'asrhyp': 'asr'}


def main(args):
    # Interpret the arguments.
    req_fields = list() if args.all else args.fields
    if 'rec' not in req_fields:
        req_fields.append('rec')  # We require the rec fname for all the
                                  # records.
    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)

    # Read in the dictionary.
    if args.dictionary:
        known_words = set(line.split()[0] for line in args.dictionary)
        args.dictionary.close()
    else:
        known_words = None

    # Extract the records.
    print 'Extracting semantics from the call logs...'
    recs = extract_trns_sems(args.infname, args.verbose, fields=req_fields,
                             ignore_list_file=args.ignore, normalise=True,
                             do_exclude=True, known_words=known_words)
    print "Total number of annotated user turns:", len(recs)

    # Save all the files in the requested format.
    if args.fields is None:
        fields = ("transcription", "semitran", "semihyp", "asrhyp")
    else:
        fields = args.fields

    for fldname in fields:
        print 'Saving {fld}s...'.format(fld=fldname)
        outfname = 'extracted.{suf}'.format(suf=_suffixes[fldname])
        write_data(args.outdir, outfname, recs,
                   '{{rec.audio}} => {{rec.{recname}}}\n'.format(
                       recname=_xmlname2recname[fldname]))
    # Print a final message.
    print 'Done.  Output written to "{outdir}".'.format(
        outdir=args.outdir + os.sep)


if __name__ == "__main__":
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
    Finds CUED XML files describing calls in the directory specified, extracts
    a couple of fields from them for each turn (transcription, ASR 1-best,
    semantics transcription, SLU 1-best) and outputs them to separate files in
    the following format:
        {wav_filename} => {field}

    It scans for 'user-transcription.norm.xml' (or `user-transcription.xml'
    if the former is not found in the log directory) to extract the
    transcriptions and the semantics.

      """)

    arger.add_argument('-i', '--infname',
                       help="an input directory with CUED audio files and "
                            "call logs or a file listing these files' "
                            "immediate parent dirs")
    arger.add_argument('-o', '--outdir', default='./cued_data',
                       help='an output directory for files with audio and '
                            'their transcription (default: ./cued_data)')
    arger.add_argument('-f', '--fields', nargs='+',
                       help='fields of the XML transcription file that '
                            'should be extracted')
    arger.add_argument('-a', '--all', action='store_true',
                       help='ignore missing values for required fields '
                            '(i.e., process all turns)')
    arger.add_argument('-d', '--dictionary',
                       type=argparse.FileType('r'),
                       metavar='FILE',
                       help='Path towards a phonetic dictionary constraining '
                            'what words should be allowed in transcriptions. '
                            'The dictionary is expected to contain the words '
                            'in the first whitespace-separated column.')
    arger.add_argument('-g', '--ignore',
                       type=argparse.FileType('r'),
                       metavar='FILE',
                       help='Path towards a file listing globs of CUED '
                            'call log files that should be ignored.\n'
                            'The globs are interpreted wrt. the current '
                            'working directory. For an example, see the '
                            'source code.')
    arger.add_argument('-v', '--verbose', action="store_true",
                       help='set verbose output')
    main(arger.parse_args())
