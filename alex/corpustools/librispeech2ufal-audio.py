#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

"""
This program processes a LibriSpeech corpus, converts all audio files
to WAVs and copies them into a destination directory along with their
transcriptions.

It looks for '*.trans.txt' files to extract transcriptions and names
of audio files.

An example ignore list file could contain the following three lines:

/some-path/call-logs/log_dir/some_id.flac
some_id.wav
jurcic-??[13579]*.wav

The first one is an example of an ignored path. On UNIX, it has to start with
a slash. On other platforms, an analogic convention has to be used.

The second one is an example of a literal glob.

The last one is an example of a more advanced glob. It says basically that
all odd dialogue turns should be ignored.

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


from alex.corpustools.cued import find_with_ignorelist

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
        number of ignored files (file basenames referred in transcription logs
                                but missing in the file system, presumably
                                because specified by one of the ignoring
                                mechanisms)

    """

    # Unpack the arguments.
    infname = args.infname
    outdir = args.outdir
    lang = args.language
    verbose = args.verbose
    ignore_list_file = args.ignore
    dict_file = args.dictionary

    size = 0
    n_overwrites = 0

    # Import the appropriate normalisation module.
    norm_mod_name = _LANG2NORMALISATION_MOD[lang]
    norm_mod = __import__(norm_mod_name, fromlist=( 'normalise_text', 'exclude_asr', 'exclude_by_dict'))

    # Read in the dictionary.
    if dict_file:
        known_words = set(line.split()[0] for line in dict_file)
        dict_file.close()
    else:
        known_words = None

    # Find transcription files.
    txt_paths = find_with_ignorelist(args.infname, '*.trans.txt', ignore_list_file)

    # Process the files.
    flac_names = []
    for txt_path in txt_paths:
        if verbose:
            print "Processing", txt_path

        path_prefix = os.path.split(txt_path)[0]
        with codecs.open(txt_path, 'r', 'UTF-8') as txt_file:
            for line in txt_file:
                # Each line contains the name of the audio file and the transcription
                (flac_name, trs) = line.split(' ', 1)
                flac_names += [flac_name]

                # Process audio file
                flac_path = os.path.join(path_prefix, flac_name + '.flac')
                wav_path = os.path.join(outdir, "{r:02}".format(r=random.randint(0, 99)), "{r:02}".format(r=random.randint(0, 99)), flac_name + '.wav')

                if not os.path.exists(os.path.dirname(wav_path)):
                    os.makedirs(os.path.dirname(wav_path))

                if not os.path.isfile(flac_path):
                    continue
                    
                to_wav(flac_path, wav_path)
                size += os.path.getsize(wav_path)
        
                # Process transcription
                if verbose:
                    print
                    print "# f:", flac_name + '.flac'
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

                if save_transcription(wav_path + '.trn', trs):
                    n_overwrites += 1

    n_collisions = len(flac_names) - len(set(flac_names))

    return size, n_collisions, n_overwrites


if __name__ == '__main__':
    wc = collections.Counter()  # word counter
    from alex.utils.ui import getTerminalSize

    # Parse arguments.
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program processes a LibriSpeech corpus, converts all audio files
      to WAVs and copies them into a destination directory along with their
      transcriptions.

      It looks for '*.trans.txt' files to extract transcriptions and names
      of audio files.
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
    arger.add_argument('-i', '--ignore',
                       type=argparse.FileType('r'),
                       metavar='FILE',
                       help='Path towards a file listing globs of '
                            'transcription files that should be ignored.\n'
                            'The globs are interpreted wrt. the current '
                            'working directory. For an example, see the '
                            'source code.')
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
   # For an example of the ignore list file, see the top of the script.
    args = arger.parse_args()

    # Do the copying.
    size, n_collisions, n_overwrites = convert(args)

    # Report.
    print "Size of transcoded audio data:", size
    msg = ("# collisions: {0};  # overwrites: {1}").format(n_collisions, n_overwrites)
    print msg

    # Print out the contents of the word counter to 'word_list'.
    with codecs.open(args.word_list, 'w', 'UTF-8') as word_list_file:
        for word in sorted(wc):
            word_list_file.write(u"{word}\t{count}\n".format(word=word, count=wc[word]))
