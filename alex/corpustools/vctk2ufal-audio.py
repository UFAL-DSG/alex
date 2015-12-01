#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

"""
This program processes a VoxForge corpus and copies all WAVs into
a destination directory along with their transcriptions.

In each subdirectory of the given directory, it looks for audio files in
the 'wav48' directory and for transcriptions in 'txt'.

"""

from __future__ import unicode_literals

import argparse
import collections
import os
import os.path
import shutil
import sys
import codecs
import pysox
import random
import glob

from xml.etree import ElementTree

# Make sure the alex package is visible.
if __name__ == '__main__':
    import autopath

from alex.utils.fs import find

_LANG2NORMALISATION_MOD = {
    'cs': 'alex.corpustools.text_norm_cs',
    'en': 'alex.corpustools.text_norm_en',
    'es': 'alex.corpustools.text_norm_es',
}

def save_transcription(trs_fname, trs):
    """
    Echoes `trs' into `trs_fname'. Returns True iff the
    output file already existed.

    """
    existed = os.path.exists(trs_fname)
    if not trs.endswith('\n'):
        trs += '\n'
    with codecs.open(trs_fname, 'w', 'UTF-8') as trs_file:
        trs_file.write(trs)
    return existed

def to_wav(src_path, wav_path):
    sox_in = pysox.CSoxStream(src_path)
    sox_out = pysox.CSoxStream(wav_path, 'w', pysox.CSignalInfo(16000, 1, 16), fileType='wav')
    sox_chain = pysox.CEffectsChain(sox_in, sox_out)
    sox_chain.add_effect(pysox.CEffect('rate', ['16000']))
    sox_chain.flow_effects()
    sox_out.close()

def convert(args):
    """
    Looks for recordings and transcriptions under the `args.infname'
    directory.  Converts audio files to WAVs and copies the .wav files
    and their transcriptions to `args.outdir' using the `extract_wavs_trns'
    function. `args.dictionary' may refer to an open file listing the only
    words to be allowed in transcriptions in the first whitespace-separated column.

    Returns a tuple of:
        number of collisions (files at different paths with same basename)
        number of overwrites (files with the same basename as previously
                             present in `args.outdir')
        number of missing files (file basenames referred in transcription logs
                                but missing in the file system)

    """

    # Unpack the arguments.
    infname = args.infname
    outdir = args.outdir
    lang = args.language
    verbose = args.verbose
    dict_file = args.dictionary

    size = 0
    n_overwrites = 0
    n_missing_audio = 0

    # Import the appropriate normalisation module.
    norm_mod_name = _LANG2NORMALISATION_MOD[lang]
    norm_mod = __import__(norm_mod_name, fromlist=( 'normalise_text', 'exclude_asr', 'exclude_by_dict'))

    # Read in the dictionary.
    if dict_file:
        known_words = set(line.split()[0] for line in dict_file)
        dict_file.close()
    else:
        known_words = None


    wavs = glob.glob(os.path.join(infname, 'wav48', '*.wav'))
    wavs.extend(glob.glob(os.path.join(infname, 'wav48', '*', '*.wav')))
    wavs.extend(glob.glob(os.path.join(infname, 'wav48', '*', '*', '*.wav')))

    fnames = []
    for fn_w in wavs:
        fn_t = fn_w.replace('wav48', 'txt').replace('wav', 'txt')

        if not os.path.exists(fn_t):
            continue

        with codecs.open(fn_t, 'r', 'UTF-8') as txt_file:
            trs = txt_file.readline().strip()
            wav_name = fn_w

            if len(wav_name) < 3:
                continue

            fname = os.path.basename(wav_name).replace('.wav', '')

            # Copy or convert audio file
            src_wav_path = wav_name
            tgt_wav_path = os.path.join(outdir, "{r:02}".format(r=random.randint(0, 99)), "{r:02}".format(r=random.randint(0, 99)), fname + '.wav')

            if not os.path.exists(os.path.dirname(tgt_wav_path)):
                os.makedirs(os.path.dirname(tgt_wav_path))

            # copy and convert the audio 
            to_wav(src_wav_path, tgt_wav_path)

            fnames += [fname]

            size += os.path.getsize(tgt_wav_path)

            # Write transcription
            if verbose:
                print
                print "# f:", wav_name + '.wav'
                print "orig transcription:", trs.upper().strip()

            trs = norm_mod.normalise_text(trs)

            if verbose:
                print "normalised trans:  ", trs

            if known_words is not None:
                excluded = norm_mod.exclude_by_dict(trs, known_words)
            else:
                excluded = norm_mod.exclude_asr(trs)
            if excluded:
                if verbose:
                    print "... excluded"
                continue

            wc.update(trs.split())

            if save_transcription(tgt_wav_path + '.trn', trs):
                n_overwrites += 1

    n_collisions = len(fnames) - len(set(fnames))

    return size, n_collisions, n_overwrites, n_missing_audio


if __name__ == '__main__':
    wc = collections.Counter()  # word counter
    from alex.utils.ui import getTerminalSize

    # Parse arguments.
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program processes a VoxForge corpus and copies all WAVs into
      a destination directory along with their transcriptions.

      In each subdirectory of the given directory, it looks for audio files in
      the 'wav' or 'flac' directory and for transcriptions in 'etc/PROMPTS'.
      """)

    arger.add_argument('infname', action="store",
                       help="the directory containing the corpus")
    arger.add_argument('outdir', action="store",
                       help='an output directory for files with audio and '
                            'their transcription')
    arger.add_argument('-v',
                       action="store_true",
                       dest="verbose",
                       help='set verbose output')
    arger.add_argument('-d', '--dictionary',
                       type=argparse.FileType('r'),
                       metavar='FILE',
                       help='Path towards a phonetic dictionary constraining '
                            'what words should be allowed in transcriptions. '
                            'The dictionary is expected to contain the words '
                            'in the first whitespace-separated column.')
    arger.add_argument('-l', '--language',
                       default='en',
                       metavar='CODE',
                       help='Code of the language (e.g., "cs", "en") of the transcriptions.')
    arger.add_argument('-w', '--word-list',
                       default='word_list',
                       metavar='FILE',
                       help='Path towards an output file to contain a list '
                            'of words that appeared in the transcriptions, '
                            'one word per line.')
    args = arger.parse_args()

    # Do the copying.
    size, n_collisions, n_overwrites, n_missing_audio = convert(args)

    # Report.
    print "Size of copied audio data:", size
    msg = ("# collisions: {0};  # overwrites: {1}; # missing recordings: {2}").format(n_collisions, n_overwrites, n_missing_audio)
    print msg

    sec = size / (16000 * 2)
    hour = sec / 3600.0
    print "Length of audio data in hours (for 16kHz 16b WAVs):", hour

    # Print out the contents of the word counter to 'word_list'.
    with codecs.open(args.word_list, 'w', 'UTF-8') as word_list_file:
        for word in sorted(wc):
            word_list_file.write(u"{word}\t{count}\n".format(word=word, count=wc[word]))
