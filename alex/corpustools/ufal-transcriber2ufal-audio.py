#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This program processes transcribed audio in Transcriber files and copies all
relevant speech segments into a destination directory.
It also extracts transcriptions and saves them alongside the copied wavs.

It scans for '*.trs' to extract transcriptions and names of wave files.

########################################################################
# An example ignore list file could contain the following three lines: #
########################################################################

/home/matej/wc/vystadial/data/call-logs/voip-0012097903339-121001_014358/jurcic-010-121001_014624_0014528_0014655.trs
jurcic-006-121001_014526_0008608_0008758.trs
jurcic-??[13579]*.trs

The first one is an example of an ignored path. On UNIX, it has to start with
a slash. On other platforms, an analogic convention has to be used.
#
The second one is an example of a literal glob.
#
The last one is an example of a more advanced glob. It says basically that
all odd dialogue turns should be ignored.

"""

import argparse
import codecs
import collections
import os
import os.path
import random
import xml.dom.minidom

# Make sure the alex package is visible.
if __name__ == '__main__':
    import autopath

from alex.utils.fs import find

_LANG2NORMALISATION_MOD = {
    'cs': 'alex.corpustools.text_norm_cs',
    'en': 'alex.corpustools.text_norm_en',
    'es': 'alex.corpustools.text_norm_es',
}

from alex.utils.ui import getTerminalSize
try:
    _term_width = getTerminalSize()[1]
except:
    _term_width = 80


def unique_str():
    """Generates a fairly unique string."""
    return hex(random.randint(0, 256 * 256 * 256 * 256 - 1))[2:]


def cut_wavs(src, tgt, start, end):
    """Cuts out the interval `start'--`end' from the wav file `src' and saves
    it to `tgt'.

    """
    existed = os.path.exists(tgt)
    cmd = ("sox", "--ignore-length", src, "-c 1 -r 16000 -b 16", tgt, "trim", str(start), str(end - start))
    print u" ".join(cmd)
    os.system(u" ".join(cmd))
    return existed


def save_transcription(trs_fname, trs):
    """
    Echoes `trs' into `trs_fname'. Returns True iff the
    output file already existed.

    """
    existed = os.path.exists(trs_fname)
    if not trs.endswith('\n'):
        trs += '\n'
    with codecs.open(trs_fname, 'w+', encoding='UTF-8') as trs_file:
        trs_file.write(trs)
    return existed


def extract_wavs_trns(_file, outdir, trs_only=False, lang='cs', verbose=False):
    """Extracts wavs and their transcriptions from the provided big wav and the
    transcriber file.

    """

    # Import the appropriate normalisation module.
    norm_mod_name = _LANG2NORMALISATION_MOD[lang]
    norm_mod = __import__(norm_mod_name,
                          fromlist=('exclude', 'normalise_text'))

    # Parse the file.
    doc = xml.dom.minidom.parse(_file)
    uturns = doc.getElementsByTagName("Sync")

    size = 0
    n_overwrites = 0
    n_missing_wav = 0
    n_missing_trs = 0
    for uturn in uturns:
        if verbose:
            print u'-' * _term_width

        # Retrieve the user turn's data.
        starttime = float(uturn.getAttribute('time').strip())
        if uturn.nextSibling.nodeType == uturn.TEXT_NODE:
            transcription = uturn.nextSibling.data.strip()
        else:
            transcription = ''
            n_missing_trs += 1
        try:
            endtime = float(
                uturn.nextSibling.nextSibling.getAttribute('time').strip())
        except:
            endtime = 9999.000

        # Construct various involved file names.
        src_wav_fname = _file.replace('.trs', '.wav')
        tgt_ext = u'-{start:07.2f}-{end:07.2f}.wav'.format(start=starttime, end=endtime)
        tgt_wav_fname = os.path.basename(_file).replace('.trs', tgt_ext)
        tgt_wav_fname = os.path.join(outdir, "{r:02}".format(r=random.randint(0, 99)), "{r:02}".format(r=random.randint(0, 99)), tgt_wav_fname)

        if not os.path.exists(os.path.dirname(tgt_wav_fname)):
            os.makedirs(os.path.dirname(tgt_wav_fname))
        
        
        transcription_file_name = tgt_wav_fname + '.trn'

        if verbose:
            print u" #f: {tgt}; # s: {start}; # e: {end}".format(
                tgt=os.path.basename(tgt_wav_fname), start=starttime, end=endtime)
            print "orig transcription:", transcription.upper().strip()

        # Normalise
        transcription = norm_mod.normalise_text(transcription)
        if verbose:
            print "normalised trans:  ", transcription

        # exclude all transcriptions
        if norm_mod.exclude_asr(transcription):
            if verbose:
                print u"  ...excluded"
            continue

        # Save the transcription and corresponding wav files.
        wc.update(transcription.split())
        n_overwrites += save_transcription(transcription_file_name,
                                           transcription)
        if not trs_only:
            try:
                cut_wavs(src_wav_fname, tgt_wav_fname, starttime, endtime)
                size += os.path.getsize(tgt_wav_fname)
            except OSError:
                n_missing_wav += 1
                print u"Missing audio file: ", tgt_wav_fname

    return size, n_overwrites, n_missing_wav, n_missing_trs


def convert(args):
    # TODO docstring
    # Unpack the arguments.
    infname = args.infname
    outdir = args.outdir
    lang = args.language
    verbose = args.verbose
    trs_only = args.only_transcriptions
    ignore_list_file = args.ignore
    # Read in the ignore list.
    ignore_paths = set()
    ignore_globs = set()
    if ignore_list_file:
        for path_or_glob in ignore_list_file:
            path_or_glob = path_or_glob.rstrip('\n')
            # For lines that list absolute paths,
            if os.path.abspath(path_or_glob) == os.path.normpath(path_or_glob):
                # add them to the list of paths to ignore.
                ignore_paths.add(path_or_glob)
            # For other lines, treat them as basename globs.
            else:
                ignore_globs.add(path_or_glob)
        ignore_list_file.close()

    # Get all but the ignored transcriptions.
    if os.path.isdir(infname):
        trs_paths = find(infname, '*.trs', mindepth=1, ignore_globs=ignore_globs, ignore_paths=ignore_paths)
    else:
        trs_paths = list()
        with open(infname, 'r') as inlist:
            for line in inlist:
                trs_paths.extend(find(line.strip(), '*.trs',
                                      mindepth=1, maxdepth=1,
                                      ignore_globs=ignore_globs,
                                      ignore_paths=ignore_paths))

    size = 0
    n_overwrites = 0
    n_missing_wav = 0
    n_missing_trs = 0
    for trs_path in trs_paths:

        if verbose:
            print u"Processing transcription file: ", trs_path

        cursize, cur_n_overwrites, cur_n_missing_wav, cur_n_missing_trs = \
            extract_wavs_trns(trs_path, outdir, trs_only, lang, verbose)
        size += cursize
        n_overwrites += cur_n_overwrites
        n_missing_wav += cur_n_missing_wav
        n_missing_trs += cur_n_missing_trs

    print u"Size of copied audio data:", size

    sec = size / (2*16000)
    hour = sec / 3600.0

    print u"Length of audio data in hours (for 16kHz 16bit WAVs output):", hour
    # Return the number of file collisions and overwrites.
    return n_overwrites, n_missing_wav, n_missing_trs


if __name__ == '__main__':
    import sys

    wc = collections.Counter()  # word counter

    # Initialisation.
    random.seed(1)
    if not sys.stdout.isatty():
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
    if not sys.stderr.isatty():
        sys.stderr = codecs.getwriter('UTF-8')(sys.stderr)
    if not sys.stdin.isatty():
        sys.stdin = codecs.getreader('UTF-8')(sys.stdin)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        This program processes transcribed audio in Transcriber (*.trs) files
        and copies all relevant speech segments into a destination directory.
        It also extracts transcriptions and saves them alongside the copied
        wavs.

        It scans for '*.trs' to extract transcriptions and names of wave files.

      """)

    parser.add_argument('infname',
                        action="store",
                        help='an input directory with trs and wav files, or '
                             'a file listing the trs files')
    parser.add_argument('outdir',
                        action="store",
                        help='an output directory for files with audio and '
                             'their transcription')
    parser.add_argument('-i', '--ignore',
                        type=argparse.FileType('r'),
                        metavar='FILE',
                        help='Path towards a file listing globs of wav files '
                             'that should be ignored.  The globs are '
                             'interpreted wrt. the current working directory. '
                             'For an example, see the source code.')
    parser.add_argument('-l', '--language',
                        default='cs',
                        metavar='CODE',
                        help='Code of the language (e.g., "cs") of the '
                             'transcriptions.')
    parser.add_argument('-t', '--only-transcriptions',
                        action="store_true",
                        help='only normalise transcriptions, ignore audio '
                             'files')
    parser.add_argument('-v',
                        action="store_true",
                        dest="verbose",
                        help='set verbose output')
    parser.add_argument('-w', '--word-list',
                        default='word_list',
                        metavar='FILE',
                        help='Path towards an output file to contain a list '
                             'of words that appeared in the transcriptions, '
                             'one word per line.')

    args = parser.parse_args()

    # Do the copying.
    n_overwrites, n_missing_wav, n_missing_trs = convert(args)

    # Report.
    msg = (u"# overwrites: {ovw};  # without transcription: {wotrs};  "
           u"# missing: {msng}").format(ovw=n_overwrites, wotrs=n_missing_trs,
                                        msng=n_missing_wav)
    print msg

    with codecs.open(args.word_list, 'w', "utf-8") as word_list_file:
        for word in sorted(wc):
            word_list_file.write(u"{word}\t{count}\n".format(word=word, count=wc[word]))
