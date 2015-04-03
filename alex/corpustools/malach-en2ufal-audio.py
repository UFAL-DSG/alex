#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

"""
This program processes the MALACH corpus, converts all audio files
to WAVs, extracts individual utterances and copies them into a destination
directory along with their transcriptions.

It looks for '*.trs' files to extract transcriptions and names
of audio files.

An example ignore list file could contain the following three lines:

/some-path/some_id.trs
some_id.trs
??[13579]*.trs

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
import xml.dom.minidom
import random


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
    cmd = ['sox', '--ignore-length', src_path, '-c', '1', '-r', '16000', '-b', '16', wav_path]
    subprocess.call(cmd)

def segment_to_wav(src_path, wav_path, start, end):
    cmd = ['sox', src_path, '-c', '1', '-r', '16000', '-b', '16', wav_path, 'trim', str(start), str(end - start)]
    subprocess.call(cmd)
    

def convert(args):
    """
    Looks for recordings and transcriptions under the `args.infname'
    directory.  Converts audio files to WAVs and copies the .wav files
    and their transcriptions to `args.outdir' directory. `args.dictionary' may
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
        number of missing transcriptions

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
    n_missing_trs = 0

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
    trs_paths = find_with_ignorelist(infname, '*.trs', ignore_list_file)
    trs_dict = {os.path.split(fpath)[1]: fpath for fpath in trs_paths}

    # Find all audio files, create dictionary of paths by basename.
    audio_paths = find_with_ignorelist(infname, '*.mp2')
    audio_dict = {os.path.splitext(os.path.split(fpath)[1])[0]: fpath for fpath in audio_paths}
    n_collisions = len(audio_paths) - len(audio_dict)

    # Process the files.
    for trs_path in trs_dict.values():
        if verbose:
            print "Processing", trs_path

        # Parse the file.
        doc = xml.dom.minidom.parse(trs_path)
        fname = doc.getElementsByTagName("Trans")[0].attributes['audio_filename'].value
        if not fname in audio_dict or not os.path.isfile(audio_dict[fname]):
            if verbose:
                print "Lost audio file:", fname
            n_missing_audio += 1
            continue
        audio_path = audio_dict[fname]

        # Convert audio to wav.
        tmp_wav_path = os.path.join(outdir, fname + '.wav')
        to_wav(audio_path, tmp_wav_path)

        turns = doc.getElementsByTagName("Turn")


        i = 0
        for turn in turns:
            i += 1

            currtime = float(turn.getAttribute('startTime'))
            currtext = ''

            utterances = []

            # Process all child nodes.
            for node in turn.childNodes:
                if node.nodeType == node.ELEMENT_NODE and node.tagName == 'Sync':
                    starttime = currtime
                    currtime = float(node.getAttribute('time'))

                    if currtime > starttime:
                        utterances += [(currtext, starttime, currtime)]

                    currtext = ''
                elif node.nodeType == node.TEXT_NODE:
                    currtext += ' ' + node.data.strip()

            # Add the last utterance, which is not followed by a Sync tag.
            starttime = currtime
            try:
                currtime = float(turn.getAttribute('endTime'))
            except ValueError:
                currtime = float(turn.getAttribute('endTime').split()[0])
            
            if currtime > starttime:
                utterances += [(currtext, starttime, currtime)]

            j = 0
            for (trs, starttime, endtime) in utterances:
                j += 1

                if (endtime - starttime) < 0.2:
                    print "Too short segment"
                    continue
                    
                if not trs: # empty transcription
                    n_missing_trs += 1

                wav_name = '%s_%02d_%04d.wav' % (fname, i, j)
                #wav_path = os.path.join(outdir, wav_name)
                wav_path = os.path.join(outdir, "{r:02}".format(r=random.randint(0, 99)), "{r:02}".format(r=random.randint(0, 99)), wav_name)

                if not os.path.exists(os.path.dirname(wav_path)):
                    os.makedirs(os.path.dirname(wav_path))

                if verbose:
                    print
                    print "src:", os.path.split(audio_path)[1]
                    print "tgt:", wav_name
                    print "time:", starttime, endtime
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

                # Extract utterance from audio.
                segment_to_wav(tmp_wav_path, wav_path, starttime, endtime)
                size += os.path.getsize(wav_path)
                seconds += endtime - starttime
        
        os.remove(tmp_wav_path)


    return size, seconds, n_collisions, n_overwrites, n_missing_audio, n_missing_trs


if __name__ == '__main__':
    wc = collections.Counter()  # word counter
    from alex.utils.ui import getTerminalSize

    # Parse arguments.
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        This program processes the MALACH corpus, converts all audio files
        to WAVs, extracts individual utterances and copies them into a destination
        directory along with their transcriptions.

        It looks for '*.trs' files to extract transcriptions and names
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
    size, seconds, n_collisions, n_overwrites, n_missing_audio, n_missing_trs = convert(args)

    # Report.
    print "Size of extracted audio data:", size
    print "Length of audio data in hours:", seconds/3600
    msg = ("# collisions: {0};  # overwrites: {1}; # missing recordings: {2}; # missing transcriptions: {3}").format(n_collisions, n_overwrites, n_missing_audio, n_missing_trs)
    print msg

    # Print out the contents of the word counter to 'word_list'.
    with codecs.open(args.word_list, 'w', 'UTF-8') as word_list_file:
        for word in sorted(wc):
            word_list_file.write(u"{word}\t{count}\n".format(word=word, count=wc[word]))
