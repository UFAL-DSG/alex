#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set fdm=marker :
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.


########################################################################
# An example ignore list file could contain the following three lines: #
########################################################################

# /home/matej/wc/vystadial/data/call-logs/voip-0012097903339-121001_014358/jurcic-010-121001_014624_0014528_0014655.wav
# jurcic-006-121001_014526_0008608_0008758.wav
# jurcic-??[13579]*.wav

# The first one is an example of an ignored path. On UNIX, it has to start with
# a slash. On other platforms, an analogic convention has to be used.
#
# The second one is an example of a literal glob.
#
# The last one is an example of a more advanced glob. It says basically that
# all odd dialogue turns should be ignored.


import argparse
import collections
import glob
import os.path
import re
import shutil
import sys
import xml.dom.minidom

import __init__

from SDS.utils.various import get_text_from_xml_node
from SDS.utils.fs import find, normalise_path

"""
This program processes CUED call log files and copies all audio into
a destination directory.
It also extracts transcriptions from the log files and saves them alongside the
copied wavs.

It scans for 'user-transcription.norm.xml' to extract transcriptions and names
of .wav files.

"""

# substitutions {{{
subst = [('GOOD-BYE', 'GOODBYE'),
         ('GOOD BYE', 'GOODBYE'),
         ('PRICE RANGE', 'PRICERANGE'),
         ('WEST SIDE', 'WESTSIDE'),
         ('KINGS HEDGES', 'KINKGSHEDGES'),
         ('RIVER SIDE', 'RIVERSIDE'),
         ('CHERRY HINTON', 'CHERRYHINTON'),
         ('FEN DITTON', 'FENDITTON'),
         ('PHONENUMBER', 'PHONE NUMBER'),
         ('OKEY', 'OK'),
         ('OKAY', 'OK'),
         ('YEP', 'YUP'),
         ('DOES\'T', 'DOESN\'T'),
         ('WHATS', 'WHAT\'S'),
         ('FO', 'FOR'),
         ('TEL', 'TELL'),
         ('BOUT', 'ABOUT'),
         ('YO', 'YOU'),
         ('RE', ''),
         ('SH', ''),
         ('CENTRE', 'CENTER'),
         ('YESYES', 'YES YES'),
         ('YESI', 'YES'),
         ('YOUWHAT', 'YOU WHAT'),
         ('YOUTELL', 'YOUTELL'),
         ('XPENSIVE', 'EXPENSIVE'),
         ('WITHWHAT', 'WITH WHAT'),
         ('WITHINTERNET', 'WITH INTERNET'),
         ('WI-FI', 'WIFI'),
         ('WHATWHAT', 'WHAT WHAT'),
         ('WHATPRICE', 'WHAT PRICE'),
         ('WHATAREA', 'WHAT AREA'),
         ('WHATTHAT', 'WHAT THAT'),
         ('WHATADDRESS', 'WHAT ADDRESS'),
         ('WANTINTERNATIONAL', 'WANT INTERNATIONAL'),
         ('WANTA', 'WANT A'),
         ('TRUMPINGTONAREA', 'TRUMPINGTON AREA'),
         ('THEVENUE', 'THE VENUE'),
         ('THEROMSEY', 'THE ROMSEY'),
         ('THEPRICERANGE', 'THE PRICERANGE'),
         ('THEPRICE', 'THE PRICE'),
         ('THEPHONE', 'THE PHONE'),
         ('THEINTERVIEW', 'THE INTERVIEW'),
         ('THEFUSION', 'THE FUSION'),
         ('THEEXPENSIVE', 'THE EXPENSIVE'),
         ('THEBEST', 'THE BEST'),
         ('THEADDRESS', 'THE ADDRESS'),
         ('THATCHILDREN', 'THAT CHILDREN'),
         ('THABK', 'THANK'),
         ('SIL', '(SIL)'),
         ('RESTAUANT', 'RESTAURANT'),
         ('RESTAURAN', 'RESTAURANT'),
         ('RESTAURANTE', 'RESTAURANT'),
         ('RESTAURANTI N', 'RESTAURANT IN'),
         ('RESTAURANTIN', 'RESTAURANT IN'),
         ('RESTURTANT', 'RESTAURANT'),
         ('REATAURANT', 'RESTAURANT'),
         ('REALLYUM', 'REALLY UM'),
         ('RANCHTHE', 'RANCH THE'),
         ('PUBMODERATE', 'PUB MODERATE'),
         ('PHONEN', 'PHONE'),
         ('OKDO', 'OK DO'),
         ('OKDOES', 'OK DOES'),
         ('OKGOODBAY', 'OKGOODBAY'),
         ('OKMAY', 'OK MAY'),
         ('OKTHANK', 'OK THANK'),
         ('OKHWAT', 'OK WHAT'),
         ('OKWHAT\'S', 'OK WHAT\'S'),
         ('PLACEWITH', 'PLACE WITH'),
         ('11', 'ELEVEN'),
         ('24', 'TWENTY FOUR'),
         ('ACONTEMPORARY', 'A CONTEMPORARY'),
         ('ADDELBROOKE\'S', 'ADDENBROOKE\'S'),
         ('ADDERSS', 'ADDRESS'),
         ('ADDESS', 'ADDRESS'),
         ('ADDRESSOF', 'ADDRESS OF'),
         ('ADDRESSPHONE', 'ADDRESS PHONE'),
         ('ADDRESSS', 'ADDRESS'),
         ('ADSRESSSIR', 'ADDRESS SIR'),
         ('ADENBROOK\'S', 'ADDENBROOK\'S'),
         ('ADRDESS', 'ADDRESS'),
         ('ADRESS', 'ADDRESS'),
         ('ANDAND', 'AND AND'),
         ('ANDAREA', 'AND AREA'),
         ('ANDCHINESE', 'AND CHINESE'),
         ('ANDENGLISH', 'AND ENGLISH'),
         ('ANDWELL', 'AND WELL'),
         ('ANDTHAT', 'AND THAT'),
         ('ANDWHAT', 'AND WHAT'),
         ('ANDWHERE', 'AND WHERE'),
         ('ANEXPENSIVE', 'AN EXPENSIVE'),
         ('ARESTAURANT', 'A RESTAURANT'),
         ('ATHAI', 'A THAI'),
         ('ATURKISH', 'A TURKISH'),
         ('BARONIN', 'BARON IN'),
         ('CASLE', 'CASTLE'),
         ('CASTE', 'CASTLE'),
         ('CASTLE HILL', 'CASTLEHILL'),
         ('CHEAPPRICERANGE', 'CHEAP PRICERANGE'),
         ('CHEAPRESTAURANT', 'CHEAP RESTAURANT'),
         ('CHIDREN', 'CHILDREN'),
         ('CHINESE', 'CHINES'),
         ('CHLIDREN', 'CHILDREN'),
         ('CINESE', 'CHINESE'),
         ('COFFEE', 'COFFE'),
         ('CONNECTIO', 'CONNECTION'),
         ('COUL', 'COULD'),
         ('DBAY', 'BAY'),
         ('DOENS\'T', 'DOESN\'T'),
         ('DOESRVE', 'DESERVE'),
         ('DOTHAT', 'DO THAT'),
         ('EXPANSIVE', 'EXPENSIVE'),
         ('EXPENSIVEE', 'EXPENSIVE'),
         ('FANTASTICTHANK', 'FANTASTIC THANK'),
         ('FENDITON', 'FENDITTON'),
         ('FINDAMERICAN', 'FIND AMERICAN'),
         ('GOO', 'GOOD'),
         ('GOODTHANK', 'GOOD THANK'),
         ('GOODWHAT', 'GOOD WHAT'),
         ('GOODYBE', 'GOODBYE'),
         ('GREATTHANK', 'GREAT THANK'),
         ('GREATWHAT', 'GRAT THANK'),
         ('HASTV', 'HAS TV'),
         ('HEGES', 'HEDGES'),
         ('HII', 'HILL'),
         ('HIL', 'HILL'),
         ('I\'\'M', 'I\'M'),
         ('IAM', 'I AM'),
         ('IAN', 'I AM'),
         ('I"M', 'I\'M'),
         ('II', 'I'),
         ('II\'M', 'I\'M'),
         ('INDIANINDIAN', 'INDIAN INDIAN'),
         ('INDITTON', 'IN DITTON'),
         ('INEXPRNSIVE', 'INEXPENSIVE'),
         ('INPRICERANGE', 'IN PRICERANGE'),
         ('KINGTHE', 'KINGTHE'),
         ('LOOKIN', 'LOOKING'),
         ('LOOKINF', 'LOOKING'),
         ('MEDITERRARANEAN', 'MEDITERRANEAN'),
         ('MIDDELE', 'MIDDLE'),
         ('MUCHHAVE', 'MUCH HAVE'),
         ('NEEDA', 'NEED A'),
         ('NEEDADDENBROOK\'S', 'NEED ADDENBROOK\'S'),
         ('NEEDEXPENSIVE', 'NEED EXPENSIVE'),
         ('NOCONTEMPORARY', 'NO CONTEMPORARY'),
         ('NODOES', 'NO DOES'),
         ('NUMBERAND', 'NUMBERAND'),
         ('3', 'THREE'),
         ('4', 'FOUR'),
         ('5', 'FIVE'),
         ('73', 'SEVENTY THREE'),
         ('ACCOMIDATION', 'ACCOMMODATION'),
         ('ACCOMODATION', 'ACCOMMODATION'),
         ('ADDELBROOKE\'S', 'ADDENBROOKE\'S'),
         ('ADDENBROOKES', 'ADDENBROOKE\'S'),
         ('ADDENSBROOKE', 'ADDENBROOKE\'S'),
         ('ADDNEBROOKE', 'ADDENBROOKE\'S'),
         ('ADENBROOKE\'S', 'ADDENBROOKE\'S'),
         ('ADDENBROOKS', 'ADDENBROOKE\'S'),
         ('ADRESSES', 'ADDRESSES'),
         ('ADRESSS', 'ADDRESS'),
         ('AIDENBROOK', 'ADDENBROOKE\'S'),
         ('ANYKIND', 'ANY KIND'),
         ('ARBORY', 'ARBURY'),
         ('CAFFE', 'CAFE'),
         ('CATHERINE\'S\'S', 'CATHERINE\'S'),
         ('CCAN', 'CAN'),
         ('CENTRAP', 'CENTRAL'),
         ('CHEERY', 'CHERY'),
         ('COFF', 'COFFEE'),
         ('COFFE', 'COFFEE'),
         ('CONNCETION', 'CONNECTION'),
         ('CONTINTENAL', 'CONTINENTAL'),
         ('DOSEN\'T', 'DOESN\'T'),
         ('DONT\'T', 'DON\'T'),
         ('ENGINERING', 'ENGINEERING'),
         ('EXPENCIVE', 'EXPENSIVE'),
         ('FANDITTON', 'FENDITTON'),
         ('FENDERTON', 'FENDITTON'),
         ('FINDA', 'FIND A'),
         ('FORDABLE', 'AFORDABLE'),
         ('GALLERIA', 'GALLERY'),
         ('GERTEN', 'GIRTON'),
         ('GERTON', 'GIRTON'),
         ('GOOD0BYE', 'GOODBYE'),
         ('GOODYE', 'GOODBYE'),
         ('HINSON', 'HINSTON'),
         ('HITTON', 'HINSTON'),
         ('MODER', 'MODERN'),
         ('MOTAL', 'MOTEL'),
         ('NUMMBER', 'NUMBER'),
         ('OPENNING', 'OPENING'),
         ('OT', 'OR'),
         ('PHONBE', 'PHONE'),
         ('PRCE', 'PRICE'),
         ('PRIZE', 'PRICE'),
         ('REASTURTANT', 'RESTAURANT'),
         ('RESTUARANT', 'RESTAURANT'),
         ('RIVESIDE', 'RIVERSIDE'),
         ('SENDETON', 'FENDITTON'),
         ('SENDINGTON', 'FENDINGTON'),
         ('SENDITTON', 'FENDITTON'),
         ('SHUSHI', 'SUSHI'),
         ('SILENCE', '(SIL)'),
         ('SILENT', '(SIL)'),
         ('SINDEENTAN', 'FENDITTON'),
         ('SINDEETAN', 'FENDITTON'),
         ('SINDINTON', 'FENDITTON'),
         ('SOMETHINGIN', 'SOMETHING IN'),
         ('TELEVISON', 'TELEVISION'),
         ('TELEVSION', 'TELEVISION'),
         ('THANH', 'THANK'),
         ('THEIRE', 'THEIR'),
         ('VENEUE', 'VENUE'),
         ('VODCA', 'VODKA'),
         ('WAHT', 'WHAT'),
         ('ADENBROOKS', 'ADDENBROOK\'S'),
         ('ARCHECTICTURE', 'ARCHITECTURE'),
         ('AVANUE', 'AVENUE'),
         ('ENTERAINMENT', 'ENTERTAINMENT'),
         ('GUESHOUSE', 'GUESTHOUSE'),
         ('ISNT', 'ISN\'T'),
         ('PHONME', 'PHONE'),
         ('OFCOURSE', 'OF COURSE'),
         ('PLCE', 'PRICE'),
         ('PONE', 'PHONE'),
         ('RESAURANT', 'RESTAURANT'),
         ('RESTAUTANT', 'RESTAURANT'),
         ('SHAMPAIN', 'CHAMPAIN'),
         ('STAION', 'STATION'),
         ('STAIONS', 'STATIONS'),
         ('TELIVISION', 'TELEVISION'),
         ('TELIVISON', 'TELEVISION'),
         ('THNK', 'THANK'),
         ('UNIVERCITY', 'UNIVERSITY'),
         ('WANNT', 'WANT'),
         ('ZIZI', 'ZIZZI'),
         ('AMARICAN', 'AMERICAN'),
         ('AWEFUL', 'AWFUL'),
         ('CHEEP', 'CHEAP'),
         ('CHINES', 'CHINESE'),
         ('DOESNT', 'DOESN\'T'),
         ('EXCELENT', 'EXCELLENT'),
         ('FENDINGTON', 'FENDITTON'),
         ('PRIVE', 'PRICE'),
         ('POSTCODE', 'POST CODE'),
         ('ZIPCODE', 'ZIP CODE'),
         ('RAODSIDE', 'ROADSIDE'),
         ('REPET', 'REPEAT'),
         ('PSOT', 'POST'),
         ('TEH', 'THE'),
         ('THAK', 'THANK'),
         ('VANUE', 'VENUE'),
         ('BEGENT', 'REGENT'),
         ('CHINE', 'CHINESE'),
         ('CHINES', 'CHINESE'),
         ('AFORDABLE', 'AFFORDABLE'),
         ('ADDRES', 'ADDRESS'),
         ('ADDENBROOKE', 'ADDENBROOKE\'S'),
         ('ANYTIHNG', 'ANYTHING'),
         ('NUMBERAND', 'NUMBER AND'),
         ('PIRCE', 'PRICE'),
         ('PRICEP', 'PRICE'),
         ('TNANK', 'THANK'),
         ('SOMTHING', 'SOMETHING'),
         ('WHNAT', 'WHAT'),
         ]
#}}}

# hesitation expressions {{{
hesitation = ['AAAA', 'AAA', 'AA', 'AAH', 'A-', "-AH-", "AH-", "AH.", "AH",
              "AHA", "AHH", "AHHH", "AHMA", "AHM", "ANH", "ARA", "-AR",
              "AR-", "-AR", "ARRH", "AW", "EA-", "-EAR", "-EECH", "\"EECH\"",
              "-EEP", "-E", "E-", "EH", "EM", "--", "ER", "ERM", "ERR",
              "ERRM", "EX-", "F-", "HM", "HMM", "HMMM", "-HO", "HUH", "HU",
              "-", "HUM", "HUMM", "HUMN", "HUMN", "HUMPH", "HUP", "HUU",
              "MM", "MMHMM", "MMM", "NAH", "OHH", "OH", "SH", "--", "UHHH",
              "UHH", "UHM", "UH'", "UH", "UHUH", "UHUM", "UMH", "UMM", "UMN",
              "UM", "URM", "URUH", "UUH", "ARRH", "AW", "EM", "ERM", "ERR",
              "ERRM", "HUMN", "UM", "UMN", "URM", "AH", "ER", "ERM", "HUH",
              "HUMPH", "HUMN", "HUM", "HU", "SH", "UH", "UHUM", "UM", "UMH",
              "URUH", "MMMM", "MMM", "OHM", "UMMM"]
# }}}

excluded_characters = ['-', '+', '(', ')', '[', ']', '{', '}', '<', '>', '0',
                       '1', '2', '3', '4', '5', '6', '7', '8', '9']


def normalization(text):
#{{{
    t = text.strip().upper()

    t = t.strip().replace(
        '    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
    for a, b in [('.', ' '), ('?', ' '), ('!', ' '), ('"', ' '), (',', ' '),
                 ('_', ' '), ]:
        t = t.replace(a, b)

    t = t.strip().replace(
        '    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
    for p, s in subst:
        t = re.sub('^' + p + ' ', s + ' ', t)
        t = re.sub(' ' + p + ' ', ' ' + s + ' ', t)
        t = re.sub(' ' + p + '$', ' ' + s, t)
        t = re.sub('^' + p + '$', s, t)

    t = t.strip().replace(
        '    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
    for p in hesitation:
        t = re.sub('^' + p + ' ', '(HESITATION) ', t)
        t = re.sub(' ' + p + ' ', ' (HESITATION) ', t)
        t = re.sub(' ' + p + '$', ' (HESITATION)', t)
        t = re.sub('^' + p + '$', '(HESITATION)', t)

    t = t.strip().replace(
        '    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')

    t = t.encode('ascii', 'ignore')

    return t
#}}}


def exclude(text):
    """
    Determines whether `text' is not good enough and should be excluded. "Good
    enough" is defined as containing none of `excluded_characters' and being
    longer than one word.

    """
#{{{
    for c in excluded_characters:
        if c in text:
            return True
    if len(text) < 2:
        return True

    return False
#}}}


wc = collections.Counter()  # word counter


def save_transcription(transcription_file_name, transcription):
    """
    Echoes `transcription' into `transcription_file_name'. Returns True iff the
    output file already existed.
    """
#{{{
    existed = os.path.exists(transcription_file_name)
    with open(transcription_file_name, 'w') as transcription_file:
        transcription_file.write(transcription.encode('ascii', 'ignore'))
    return existed
#}}}


def extract_wavs_trns(file_, outdir, wav_mapping, verbose):
    """Extracts wavs and their transcriptions from the named in `file_', a CUED
    call log file. Extracting means copying them to `outdir'. Returns the total
    size of audio files copied to `outdir', the number of overwritten files
    by the output files, and the number of files that were missing from the
    `wav_mapping' dictionary.

    """
#{{{
    # load the file
    doc = xml.dom.minidom.parse(file_)
    els = doc.getElementsByTagName("userturn")

    size = 0
    n_overwrites = 0
    n_missing = 0
    for el in els:
        transcription = el.getElementsByTagName("transcription")
        audio_els = el.getElementsByTagName("rec")

        if len(transcription) != 1 or len(audio_els) != 1:
            # skip this node, it contains multiple elements of either
            # transcription or audio.
            continue

        audio_basename = audio_els[0].getAttribute('fname').strip()
        # Check whether this file should be ignored.
        if audio_basename in wav_mapping:
            transcription = get_text_from_xml_node(
                transcription[0]).encode('ascii', 'ignore')
            if verbose:
                print '-' * 120
                print " # f:", audio_basename, "t:", transcription

            transcription = normalization(transcription)
            if verbose:
                print " # f:", audio_basename, "t:", transcription

            if exclude(transcription):
                continue

            wc.update(transcription.split())
            if verbose:
                print " # f:", audio_basename, "t:", transcription

            audio_file_name = wav_mapping[audio_basename]
            transcription_file_name = \
                os.path.join(outdir, audio_basename + '.trn')

            try:
                size += os.path.getsize(audio_file_name)
            except OSError:
                print "Lost audio file:", audio_file_name
            else:
                try:
                    shutil.copy2(audio_file_name, outdir)
                except shutil.Error as e:
                    print >>sys.stderr, \
                        "Isn't the `outdir' with previously copied files "\
                        "below `indir_audio' within the filesystem?\n"
                    raise e
                n_overwrites += save_transcription(transcription_file_name,
                                                   transcription)
                shutil.copystat(file_, transcription_file_name)
        else:
            n_missing += 1
            if args.verbose:
                print '-' * 120
                print "(WW) Ignoring or missing the file '{}'."\
                    .format(audio_basename)

    if verbose:
        print '-' * 120
        print
    return size, n_overwrites, n_missing
#}}}


def convert(args):
    """
    Looks for .wav files and transcription logs under the `args.indir'
    directory.  Copies .wav files and their transcriptions linked from the log
    to `args.outdir' using the `args.extract_wavs_trns' function.

    Returns a tuple of:
        number of collisions (files at different paths with same basename)
        number of overwrites (files with the same basename as previously
                             present in `args.outdir')
        number of ingored files (file basenames referred in transcription logs
                                but missing in the file system, presumably
                                because specified by one of the ignoring
                                mechanisms)

    """
#{{{
    # Unpack the arguments.
    indir = args.indir
    indir_audio = args.indir_audio
    outdir = args.outdir
    verbose = args.verbose
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
    # Get all but the ignored .wav files.
    wav_paths = find(indir_audio, '*.wav',
                     ignore_globs=ignore_globs, ignore_paths=ignore_paths)
    wav_mapping = dict()
    # Map file basenames to their relative paths -- NOTE this can be
    # destructive if multiple files have the same basename.
    for fpath in wav_paths:
        wav_basename = os.path.basename(fpath)
        wav_mapping[wav_basename] = fpath
    n_collisions = len(wav_paths) - len(wav_mapping)

    # Get all transcription logs.
    trn_paths = find(indir, 'user-transcription.norm.xml')

    if len(trn_paths) < 2:
        # Search for unnormalised transcription logs.
        print "Normalised transriptions were NOT found. Using unnormalised "\
              "transcriptions!"
        trn_paths.update(find(indir, 'user-transcription.xml'))

    # Copy files referred in the transcription logs to `outdir'.
    size = 0
    n_overwrites = 0
    n_missing = 0
    for trn_path in trn_paths:
        if verbose:
            print "Processing call log file: ", trn_path

        cursize, cur_n_overwrites, cur_n_missing = \
            extract_wavs_trns(trn_path, outdir, wav_mapping, verbose)
        size += cursize
        n_overwrites += cur_n_overwrites
        n_missing += cur_n_missing

    # Print statistics.
    print "Size of copied audio data:", size

    sec = size / (16000 * 2)
    hour = sec / 3600.0

    print "Length of audio data in hours (for 16kHz 16b WAVs):", hour
    # Return the number of file collisions and overwrites.
    return n_collisions, n_overwrites, n_missing
#}}}


if __name__ == '__main__':
    # Parse arguments. {{{
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program processes CUED call log files and copies all audio into
      a destination directory.
      It also extracts transcriptions from the log files and saves them
      alongside the copied wavs.

      It scans for 'user-transcription.norm.xml' to extract transcriptions and
      names of .wav files.

      """)

    parser.add_argument('indir', action="store",
                        help='an input directory with CUED call log files')
    parser.add_argument('indir_audio', action="store",
                        help='an input directory with CUED audio files')
    parser.add_argument('outdir', action="store",
                        help='an output directory for files with audio and '\
                             'their transcription')
    parser.add_argument('-v',
                        action="store_true",
                        default=False,
                        dest="verbose",
                        help='set verbose output')
    parser.add_argument('-i', '--ignore',
                        type=argparse.FileType('r'),
                        metavar='FILE',
                        help='Path towards a file listing globs of CUED '\
                             'call log files that should be ignored.\n'\
                             'The globs are interpreted wrt. the current '\
                             'working directory. For an example, see the '\
                             'source code.')
    # For an example of the ignore list file, see the top of the script.
    parser.add_argument('-c', '--count-ignored',
                        action="store_true",
                        default=False,
                        help='output number of files ignored due to the -i '\
                             'option')

    args = parser.parse_args()
    #}}}

    # Do the copying.
    n_collisions, n_overwrites, n_ignores = convert(args)

    # Report.
    msg = "# collisions: {};  # overwrites: {}"\
        .format(n_collisions, n_overwrites)
    if args.count_ignored:
        msg += ";  # ignores: {}".format(n_ignores)
    print msg

    # Print out the contents of the word counter to 'word_list'.
    # FIXME: Prevent overwrite.
    with open('word_list', 'w') as word_list_file:
        for w in sorted(wc):
            word_list_file.write(
                "{}\t{}\n".format(
                    w.encode('ascii', 'ignore'), wc[w]))
