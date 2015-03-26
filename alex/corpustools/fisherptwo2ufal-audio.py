#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

"""
This program processes the Fisher Part 2 corpus, converts all audio files
to WAVs, extracts individual utterances and copies them into a destination
directory along with their transcriptions.

It looks for '*.txt' files to extract transcriptions and names
of audio files.

An example ignore list file could contain the following three lines:

/some-path/some_id.txt
some_id.txt
fe_3_??[13579]*.txt

The first one is an example of an ignored path. On UNIX, it has to start with
a slash. On other platforms, an analogic convention has to be used.

The second one is an example of a literal glob.

The last one is an example of a more advanced glob.

"""

from __future__ import unicode_literals

import argparse
import collections
import os
import os.path
import subprocess
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
    and their transcriptions to `args.outdir' function. `args.dictionary' may
    refer to an open file listing the only words to be allowed in
    transcriptions in the first whitespace-separated column.

    Returns a tuple of:
        total audio size
        total audio length in seconds
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
    ignore_list_file = args.ignore
    dict_file = args.dictionary

    size = 0
    seconds = 0
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

    # Find transcription files.
    txt_paths = find_with_ignorelist(infname, 'fe_*.txt', ignore_list_file)

    # Find all audio files, create dictionary of paths by basename.
    sph_paths = find_with_ignorelist(infname, 'fe_*.sph')
    sph_dict = {os.path.split(fpath)[1]: fpath for fpath in sph_paths}
    n_collisions = len(sph_paths) - len(sph_dict)

    # Process the files.
    for txt_path in txt_paths:
        if verbose:
            print "Processing", txt_path

        txt_name = os.path.split(txt_path)[1]
        src_name = os.path.splitext(txt_name)[0]
        sph_name = src_name + '.sph'

        if not sph_name in sph_dict or not os.path.isfile(sph_dict[sph_name]):
            if verbose:
                print "Lost audio file:", sph_name
            n_missing_audio += 1
            continue

        sph_path = sph_dict[sph_name]

        utterances = []

        with codecs.open(txt_path, 'r', 'UTF-8') as txt_file:
            i = 1
            for line in txt_file:
                if len(line.strip()) == 0 or line.strip()[0] == '#': continue #ignore comments and empty lines

                # Each line contains start time, end time, speaker id and transcription
                (start, end, speaker, trs) = line.split(' ', 3)
                start = float(start)
                end = float(end)
                channel = 1 if speaker[0] == 'A' else 2
                utterances += [{'start': start, 'end': end, 'trs': trs, 'channel': channel}]
                
                i += 1

        for i in range(len(utterances)):
            utt = utterances[i]
            trs = utt['trs']

            wav_name = '%s_%03d.wav' % (src_name, i)
#            wav_path = os.path.join(outdir, wav_name)
            wav_path = os.path.join(outdir, "{r:02}".format(r=random.randint(0, 99)), "{r:02}".format(r=random.randint(0, 99)), wav_name)

            if not os.path.exists(os.path.dirname(wav_path)):
                os.makedirs(os.path.dirname(wav_path))


            if verbose:
                print
                print "src:", sph_name
                print "tgt:", wav_name
                print "time:", utt['start'], utt['end']
                print "channel:", utt['channel']
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

            # Check for very short utterances
            if utt['end']-utt['start'] < 1:
                if verbose:
                    print "... too short"
                continue

            wc.update(trs.split())

            if save_transcription(wav_path + '.trn', trs):
                n_overwrites += 1

            # Extract utterance from audio
            tmp_path = wav_path + '.tmp'
            cmd = ['sph2pipe', '-f', 'wav', '-t', '%f:%f' % (utt['start'], utt['end']), '-c', str(utt['channel']), sph_path, tmp_path]
            subprocess.call(cmd)

            # Convert to valid WAV
            to_wav(tmp_path, wav_path)
            os.remove(tmp_path)
            size += os.path.getsize(wav_path)
            seconds += utt['end'] - utt['start']

    return size, seconds, n_collisions, n_overwrites, n_missing_audio


if __name__ == '__main__':
    wc = collections.Counter()  # word counter
    from alex.utils.ui import getTerminalSize

    # Parse arguments.
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program processes the Fisher Part 2 corpus, converts all audio files
      to WAVs, extracts individual utterances and copies them into a destination
      directory along with their transcriptions.

      It looks for '*.txt' files to extract transcriptions and names
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
    

    if os.system("which sph2pipe >/dev/null 2>&1") != 0:
        print "sph2pipe not found. Please add it to your PATH and try again."
        sys.exit(1)

    # Do the copying.
    size, seconds, n_collisions, n_overwrites, n_missing_audio = convert(args)

    # Report.
    print "Size of extracted audio data:", size
    print "Length of audio data in hours:", seconds/3600
    msg = ("# collisions: {0};  # overwrites: {1}; # missing recordings: {2}").format(n_collisions, n_overwrites, n_missing_audio)
    print msg

    # Print out the contents of the word counter to 'word_list'.
    with codecs.open(args.word_list, 'w', 'UTF-8') as word_list_file:
        for word in sorted(wc):
            word_list_file.write(u"{word}\t{count}\n".format(word=word, count=wc[word]))
