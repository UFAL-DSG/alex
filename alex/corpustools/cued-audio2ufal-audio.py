#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

"""
This program processes CUED call log files and copies all audio into
a destination directory.
It also extracts transcriptions from the log files and saves them alongside the
copied wavs.

It scans for 'user-transcription.norm.xml' to extract transcriptions and names
of .wav files.

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

import argparse
import collections
import os
import os.path
import shutil
import sys
import codecs
import random

from xml.etree import ElementTree

if __name__ == "__main__":
    import autopath

from alex.corpustools.cued import find_wavs
from alex.corpustools.text_norm_en import exclude_asr, exclude_by_dict, normalise_text


def save_transcription(trs_fname, trs):
    """
    Echoes `trs' into `trs_fname'. Returns True iff the
    output file already existed.

    """
    existed = os.path.exists(trs_fname)
    with codecs.open(trs_fname, 'w', 'UTF-8') as trs_file:
        trs_file.write(trs)
    return existed


def extract_wavs_trns(dirname, sess_fname, outdir, wav_mapping,
                      known_words=None, verbose=False):
    """Extracts wavs and their transcriptions from the named in `sess_fname',
    a CUED call log file. Extracting means copying them to `outdir'. Recordings
    themselves are expected to reside in `dirname'.

    If `known_words', a collection of words present in the phonetic dictionary,
    is provided, transcriptions are excluded which contain other words. If
    `known_words' is not provided, excluded are transcriptions that contain any
    of _excluded_characters.

    Returns the total size of audio files copied to `outdir', the number of
    overwritten files by the output files, the number of wav files that were
    missing from the `wav_mapping' dictionary, and the number of transcriptions
    not present for existing recordings.

    """
    # Parse the file.
    try:
        doc = ElementTree.parse(sess_fname)
    except IOError as error:
        if verbose:
            print '!!! Could not parse "{fname}": {msg!s}.'.format(fname=sess_fname, msg=error)
            return 0, 0, 0, 0
    uturns = doc.findall(".//userturn")

    annotations = doc.findall('.//annotation')
    print "# annotations: ", len(annotations)
    if len(annotations) > 1:
        # FIXME: This is bad! We waste about 1/3 of all data from CF. However, it is not possible to deduce
        # what transcription to use.
        print "Transcription was rejected as we have more then two transcriptions and " \
              "we cannot decide which one is better."
        return 0, 0, 0, 0
    for a in annotations:
        r = False
        if 'worker_id' in a.attrib and a.attrib['worker_id'] == '19113916':
            r = True

        if r:
            print "Transcription was rejected because of unreliable annotator."
            return 0, 0, 0, 0


    size = 0
    n_overwrites = 0
    n_missing_wav = 0
    n_missing_trs = 0
    for uturn in uturns:
        # trs.text = uturn.getElementsByTagName("trs.text")
        # rec = uturn.getElementsByTagName("rec")
        rec = uturn.find("rec")
        trs = uturn.find("transcription")
        if trs is None:
            # this may be CF style transcription

            trs2 = uturn.find("transcriptions")
            if trs2 is not None:
                trs3 = trs2.findall("transcription")

                if trs3 is None:
                    if rec is not None:
                        n_missing_trs += 1
                    continue
                else:
                    trs = trs3[-1].text
            else:
                continue
        else:
            trs = trs.text

        # Check this is the wav from this directory.
        wav_basename = rec.attrib['fname'].strip()
        if wav_basename in wav_mapping:
            wav_fname = os.path.join(wav_mapping[wav_basename], wav_basename)
            if os.path.dirname(wav_fname) != dirname:
                missing_wav = True
            else:
                missing_wav = False
        else:
            missing_wav = True

        if not missing_wav:
            if verbose:
                term_width = getTerminalSize()[1] or 80
                print '-' * term_width
                print "# f:", wav_basename
                print "orig transcription:", trs.upper().strip()

            trs = normalise_text(trs)
            
            if verbose:
                print "normalised trans:  ", trs

            if known_words is not None:
                excluded = exclude_by_dict(trs, known_words)
            else:
                excluded = exclude_asr(trs)
            if excluded:
                print "... excluded"
                continue

            wc.update(trs.split())

#            trs_fname = os.path.join(outdir, wav_basename + '.trn')
            sub_dir = "{r:02}".format(r=random.randint(0, 99)), "{r:02}".format(r=random.randint(0, 99))
            trs_fname = os.path.join(outdir, sub_dir[0], sub_dir[1], wav_basename + '.trn')
            if not os.path.exists(os.path.dirname(trs_fname)):
                os.makedirs(os.path.dirname(trs_fname))

            try:
                szx = os.path.getsize(wav_fname)
            except OSError:
                print "Lost audio file:", wav_fname
            else:
                try:
                    #shutil.copy2(wav_fname, outdir)
#                    tgt = os.path.join(outdir, os.path.basename(wav_fname))
                    tgt = os.path.join(outdir, sub_dir[0], sub_dir[1], os.path.basename(wav_fname))
                    cmd = "sox --ignore-length {src} -c 1 -r 16000 -b 16 {tgt}".format(src=wav_fname, tgt=tgt)
                    print cmd
                    os.system(cmd)
                    size += os.path.getsize(tgt)
                except shutil.Error as e:
                    print >>sys.stderr, \
                        ("Isn't the `outdir' with previously copied files "
                         "below `infname' within the filesystem?\n")
                    raise e
                n_overwrites += save_transcription(trs_fname, trs)
                shutil.copystat(sess_fname, trs_fname)
        else:
            n_missing_wav += 1
            if args.verbose:
                term_width = getTerminalSize()[1] or 80
                print '-' * term_width
                print "(WW) Ignoring or missing_wav the file '{0}'."\
                    .format(wav_basename)

    if verbose:
        term_width = getTerminalSize()[1] or 80
        print '-' * term_width
        print
    return size, n_overwrites, n_missing_wav, n_missing_trs


def convert(args):
    """
    Looks for .wav files and transcription logs under the `args.infname'
    directory.  Copies .wav files and their transcriptions linked from the log
    to `args.outdir' using the `extract_wavs_trns' function. `args.dictionary'
    may refer to an open file listing the only words to be allowed in
    transcriptions in the first whitespace-separated column.

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
    verbose = args.verbose
    ignore_list_file = args.ignore
    dict_file = args.dictionary
    # Read in the dictionary.
    if dict_file:
        known_words = set(line.split()[0] for line in dict_file)
        dict_file.close()
    else:
        known_words = None

    # Find wavs.
    wav_paths = find_wavs(infname, ignore_list_file=ignore_list_file)
    # Map file basenames to their relative paths -- NOTE this can be
    # destructive if multiple files have the same basename.
    # Wav_mapping: wav basename -> path to call log dir
    swapped = [os.path.split(fpath) for fpath in wav_paths]
    wav_mapping = {name: prefix for (prefix, name) in swapped}
    n_collisions = len(wav_paths) - len(wav_mapping)

    # XXX Obsoleted since this should now be done by the `find_wavs' function
    # itself.  Yes, it does not match basenames but whole paths, still it
    # should work because all paths are normalised and absolutised.
    #
    # # Get basename for ignore files and we do NOT care about collisions
    # # ignore_wav_mapping: wav basename -> path to call log dir
    # swapped = [os.path.split(fpath) for fpath in ignore_wav_paths]
    # ignore_wav_mapping = dict([(name, prefix) for (prefix, name) in swapped])
    #
    # # Delete ignore basenames from wav_mapping (if any pass through
    # # ignore_paths and globs)
    # for ignore_basename, ignore_prefix in ignore_wav_mapping.iteritems():
    #     if ignore_basename in wav_mapping:
    #         if verbose:
    #             ignore_path = os.path.join(ignore_prefix, ignore_basename)
    #             print 'Wav file SKIPPED:', ignore_path
    #         # Removing the ignore_basename from wav_mapping
    #         del wav_mapping[ignore_basename]

    # Get all transcription logs.
    n_notnorm_trss = 0
    n_missing_trss = 0
    # XXX ???
    # path session file name created from call log dir
    sess_fnames = dict()
    # Call dir == prefix
    for prefix in wav_mapping.itervalues():
        norm_fname = os.path.join(prefix, 'user-transcription.norm.xml')
        if os.path.isfile(norm_fname):
            sess_fnames[prefix] = norm_fname
        else:
            basic_fname = os.path.join(prefix, 'user-transcription.xml')
            if os.path.isfile(basic_fname):
                sess_fnames[prefix] = basic_fname
                n_notnorm_trss += 1
            else:
                basic_fname = os.path.join(prefix,
                                           'user-transcription-all.xml')
                if os.path.isfile(basic_fname):
                    sess_fnames[prefix] = basic_fname
                    n_notnorm_trss += 1
                else:
                    n_missing_trss += 1
    # trn_paths = find(infname, 'user-transcription.norm.xml')

    print ""
    print "Number of sessions                   :", len(sess_fnames)
    print "Number of unnormalised transcriptions:", n_notnorm_trss
    print "Number of missing transcriptions     :", n_missing_trss
    print ""

    # Copy files referred in the transcription logs to `outdir'.
    size = 0
    n_overwrites = 0
    n_missing_wav = 0
    n_missing_trs = 0
    # for trn_path in trn_paths:
    for prefix, call_log in sess_fnames.iteritems():
        if verbose:
            print "Processing call log dir:", prefix
            print " session file name:     ", call_log

        cursize, cur_n_overwrites, cur_n_missing_wav, cur_n_missing_trs = \
            extract_wavs_trns(prefix, call_log, outdir, wav_mapping, known_words, verbose)
        size += cursize
        n_overwrites += cur_n_overwrites
        n_missing_wav += cur_n_missing_wav
        n_missing_trs += cur_n_missing_trs

    # Print statistics.
    print "Size of copied audio data:", size

    sec = size / (16000 * 2)
    hour = sec / 3600.0

    print "Length of audio data in hours (for 16kHz 16b WAVs):", hour
    # Return the number of file collisions and overwrites.
    return n_collisions, n_overwrites, n_missing_wav, n_missing_trs


if __name__ == '__main__':
    wc = collections.Counter()  # word counter
    from alex.utils.ui import getTerminalSize

    # Parse arguments.
    arger = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program processes CUED call log files and copies all audio into
      a destination directory.
      It also extracts transcriptions from the log files and saves them
      alongside the copied wavs.

      It scans for 'user-transcription.norm.xml' to extract transcriptions and
      names of .wav files.

      """)

    arger.add_argument('infname', action="store",
                       help="an input directory with CUED audio files and "
                            "call logs or a file listing these files' "
                            "immediate parent dirs")
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
                       help='Path towards a file listing globs of CUED '
                            'call log files that should be ignored.\n'
                            'The globs are interpreted wrt. the current '
                            'working directory. For an example, see the '
                            'source code.')
    arger.add_argument('-w', '--word-list',
                       default='word_list',
                       metavar='FILE',
                       help='Path towards an output file to contain a list '
                            'of words that appeared in the transcriptions, '
                            'one word per line.')
   # For an example of the ignore list file, see the top of the script.
    arger.add_argument('-c', '--count-ignored',
                       action="store_true",
                       default=False,
                       help='output number of files ignored due to the -i '
                            'option')
    args = arger.parse_args()

    # Do the copying.
    n_collisions, n_overwrites, n_ignores, n_missing_trs = convert(args)

    # Report.
    msg = ("# collisions: {0};  # overwrites: {1};  # without transcription: "
           "{2}")\
        .format(n_collisions, n_overwrites, n_missing_trs)
    if args.count_ignored:
        msg += ";  # ignores: {0}".format(n_ignores)
    print msg

    # Print out the contents of the word counter to 'word_list'.
    with codecs.open(args.word_list, 'w', "UTF-8") as word_list_file:
        for word in sorted(wc):
            word_list_file.write(u"{word}\t{count}\n".format(word=word, count=wc[word]))
