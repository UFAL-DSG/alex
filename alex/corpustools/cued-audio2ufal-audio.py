#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set fdm=marker :
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

"""
This program processes CUED call log files and copies all audio into
a destination directory.
It also extracts transcriptions from the log files and saves them alongside the
copied wavs.

It scans for 'user-transcription.norm.xml' to extract transcriptions and names
of .wav files.

########################################################################
# An example ignore list file could contain the following three lines: #
########################################################################

/home/matej/wc/vystadial/data/call-logs/voip-0012097903339-121001_014358/jurcic-010-121001_014624_0014528_0014655.wav
jurcic-006-121001_014526_0008608_0008758.wav
jurcic-??[13579]*.wav

The first one is an example of an ignored path. On UNIX, it has to start with
a slash. On other platforms, an analogic convention has to be used.
#
The second one is an example of a literal glob.
#
The last one is an example of a more advanced glob. It says basically that
all odd dialogue turns should be ignored.

"""

import argparse
import collections
import os.path
import re
import shutil
import sys

from xml.etree import ElementTree


# nonspeech event transcriptions {{{
_nonspeech_map = {
    '_SIL_': (
        '(SIL)',
        '(QUIET)',
        '(CLEARING)'),
    '_INHALE_': (
        '(BREATH)',
        '(BREATHING)',
        '(SNIFFING)'),
    '_LAUGH_': (
        '(LAUGH)',
        '(LAUGHING)'),
    '_EHM_HMM_': (
        '(HESITATION)',
        '(HESITATION)'),
    '_NOISE_': (
        '(COUCHING)',
        '(COUGH)',
        '(COUGHING)',
        '(LIPSMACK)',
        '(POUNDING)',
        '(RING)',
        '(RINGING)',
        '(INTERFERENCE)',
        '(KNOCKING)',
        '(BANG)',
        '(BANGING)',
        '(BACKGROUNDNOISE)',
        '(BABY)',
        '(BARK)',
        '(BARKING)',
        '(NOISE)',
        '(NOISES)',
        '(SCRAPE)',
        '(SQUEAK)',
        '(TVNOISE)')
    }
#}}}
_nonspeech_trl = dict()
for uscored, forms in _nonspeech_map.iteritems():
    for form in forms:
        _nonspeech_trl[form] = uscored


def to_wholeword_pats(substs):
    """In a list of tuples (word, substitution), makes each word into a regexp
    matching the original word, but only as a standalone word.

    """


# substitutions {{{
_subst = [('GOOD-BYE', 'GOODBYE'),
          ('GOOD BYE', 'GOODBYE'),
          ('PRICERANGE', 'PRICE RANGE'),
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
          ('YOUTELL', 'YOU TELL'),
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
          ('ANYTIHNG', 'ANYTHING'),
          ('NUMBERAND', 'NUMBER AND'),
          ('PIRCE', 'PRICE'),
          ('PRICEP', 'PRICE'),
          ('TNANK', 'THANK'),
          ('SOMTHING', 'SOMETHING'),
          ('WHNAT', 'WHAT'),
          ]
#}}}
for idx, tup in enumerate(_subst):
    pat, sub = tup
    _subst[idx] = (re.compile(ur'\b{pat}\b'.format(pat=pat)), sub)

# hesitation expressions {{{
_hesitation = ['AAAA', 'AAA', 'AA', 'AAH', 'A-', "-AH-", "AH-", "AH.", "AH",
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
for idx, word in enumerate(_hesitation):
    _hesitation[idx] = re.compile(ur'\b{word}\b'.format(word=word))

_excluded_characters = ['-', '+', '(', ')', '[', ']', '{', '}', '<', '>', '0',
                        '1', '2', '3', '4', '5', '6', '7', '8', '9']

_more_spaces = re.compile(r'\s{2,}')
_sure_punct_rx = re.compile(r'[.?!",_]')
_parenthesized_rx = re.compile(r'\(+([^)]*)\)+')


def normalise_trs(text):
#{{{
    text = _sure_punct_rx.sub(' ', text)
    text = text.strip().upper()
    text = _more_spaces.sub(' ', text)
    # Do dictionary substitutions.
    for pat, sub in _subst:
        text = pat.sub(sub, text)
    for word in _hesitation:
        text = word.sub('(HESITATION)', text)
    # Handle non-speech events (separate them from words they might be
    # agglutinated to, remove doubled parentheses, and substitute the known
    # non-speech events with the forms with underscores).
    #
    # This step can incur superfluous whitespace.
    if '(' in text:
        text = _parenthesized_rx.sub(r' (\1) ', text)
        for parenized, uscored in _nonspeech_trl.iteritems():
            text = text.replace(parenized, uscored)
        text = _more_spaces.sub(' ', text.strip())

    return text.encode('ascii', 'ignore')
#}}}


def exclude(text):
    """
    Determines whether `text' is not good enough and should be excluded. "Good
    enough" is defined as containing none of `_excluded_characters' and being
    longer than one word.

    """
#{{{
    for c in _excluded_characters:
        if c in text:
            return True
    if len(text) < 2:
        return True

    return False
#}}}


def exclude_by_dict(text, known_words):
    """Determines whether text is not good enough and should be excluded.

    "Good enough" is defined as having all its words present in the
    `known_words' collection."""
    return not all(map(lambda word: word in known_words, text.split()))


def save_transcription(trs_fname, trs):
    """
    Echoes `trs' into `trs_fname'. Returns True iff the
    output file already existed.

    """
#{{{
    existed = os.path.exists(trs_fname)
    with open(trs_fname, 'w') as trs_file:
        trs_file.write(trs.encode('ascii', 'ignore'))
    return existed
#}}}


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
#{{{
    # Parse the file.
    try:
        doc = ElementTree.parse(sess_fname)
    except IOError as error:
        if verbose:
            print '!!! Could not parse "{fname}": {msg!s}.'\
                .format(fname=sess_fname, msg=error)
            return 0, 0, 0, 0
    uturns = doc.findall(".//userturn")

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
            if rec is not None:
                n_missing_trs += 1
            continue
        else:
            trs = trs.text

        # Check whether this wav should be ignored.
        wav_basename = rec.attrib['fname'].strip()
        if wav_basename in wav_mapping:
            # Check it is the wav from this directory.
            wav_fname = wav_mapping[wav_basename]
            if os.path.dirname(wav_fname) != dirname:
                missing_wav = True
            else:
                missing_wav = False
        else:
            missing_wav = True

        if not missing_wav:
            if verbose:
                term_width = getTerminalSize()[1] or 120
                print '-' * term_width
                print " # f:", wav_basename, "t:", trs

            trs = normalise_trs(trs)
            if verbose:
                print "  after normalisation:", trs

            if known_words is not None:
                excluded = exclude_by_dict(trs, known_words)
            else:
                excluded = exclude(trs)
            if excluded:
                print "  ...excluded"
                continue

            wc.update(trs.split())

            trs_fname = os.path.join(outdir, wav_basename + '.trn')

            try:
                size += os.path.getsize(wav_fname)
            except OSError:
                print "Lost audio file:", wav_fname
            else:
                try:
                    shutil.copy2(wav_fname, outdir)
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
                term_width = getTerminalSize()[1] or 120
                print '-' * term_width
                print "(WW) Ignoring or missing_wav the file '{0}'."\
                    .format(wav_basename)

    if verbose:
        term_width = getTerminalSize()[1] or 120
        print '-' * term_width
        print
    return size, n_overwrites, n_missing_wav, n_missing_trs
#}}}


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
#{{{
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
    if os.path.isdir(infname):
        wav_paths = find(infname, '*.wav',
                         ignore_globs=ignore_globs, ignore_paths=ignore_paths)
    else:
        wav_paths = list()
        with open(infname, 'r') as inlist:
            for line in inlist:
                wav_paths.extend(find(line.strip(), '*.wav',
                                      mindepth=1, maxdepth=1,
                                      ignore_globs=ignore_globs,
                                      ignore_paths=ignore_paths))
    wav_mapping = dict()  # wav basename -> full path
    sess_fnames = dict()  # path to call log dir -> session file name
    # Map file basenames to their relative paths -- NOTE this can be
    # destructive if multiple files have the same basename.
    for fpath in wav_paths:
        prefix, wav_basename = os.path.split(fpath)
        wav_mapping[wav_basename] = fpath
        sess_fnames[prefix] = None
    n_collisions = len(wav_paths) - len(wav_mapping)

    # Get all transcription logs.
    n_notnorm_trss = 0
    n_missing_trss = 0
    for prefix in sess_fnames:
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
    sess_fnames = dict(item for item in sess_fnames.iteritems()
                       if item[1] is not None)
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
    for prefix in sess_fnames:
        if verbose:
            print "Processing call log dir: ", prefix

        cursize, cur_n_overwrites, cur_n_missing_wav, cur_n_missing_trs = \
            extract_wavs_trns(prefix, sess_fnames[prefix], outdir, wav_mapping,
                              known_words, verbose)
            # extract_wavs_trns(trn_path, outdir, wav_mapping, verbose)
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
#}}}


if __name__ == '__main__':
    wc = collections.Counter()  # word counter
    import autopath
    from alex.utils.fs import find
    from alex.utils.ui import getTerminalSize

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

    # parser.add_argument('infname', action="store",
                        # help='an input directory with CUED call log files')
    parser.add_argument('infname', action="store",
                        help="an input directory with CUED audio files and "
                             "call logs or a file listing these files' "
                             "immediate parent dirs")
    parser.add_argument('outdir', action="store",
                        help='an output directory for files with audio and '
                             'their transcription')
    parser.add_argument('-v',
                        action="store_true",
                        dest="verbose",
                        help='set verbose output')
    parser.add_argument('-d', '--dictionary',
                        type=argparse.FileType('r'),
                        metavar='FILE',
                        help='Path towards a phonetic dictionary constraining '
                             'what words should be allowed in transcriptions. '
                             'The dictionary is expected to contain the words '
                             'in the first whitespace-separated column.')
    parser.add_argument('-i', '--ignore',
                        type=argparse.FileType('r'),
                        metavar='FILE',
                        help='Path towards a file listing globs of CUED '
                             'call log files that should be ignored.\n'
                             'The globs are interpreted wrt. the current '
                             'working directory. For an example, see the '
                             'source code.')
    parser.add_argument('-w', '--word-list',
                        default='word_list',
                        metavar='FILE',
                        help='Path towards an output file to contain a list '
                             'of words that appeared in the transcriptions, '
                             'one word per line.')
    # For an example of the ignore list file, see the top of the script.
    parser.add_argument('-c', '--count-ignored',
                        action="store_true",
                        default=False,
                        help='output number of files ignored due to the -i '\
                             'option')

    args = parser.parse_args()
    #}}}

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
    # FIXME: Prevent overwrite.
    with open(args.word_list, 'w') as word_list_file:
        for w in sorted(wc):
            word_list_file.write(
                "{0}\t{1}\n".format(
                    w.encode('ascii', 'ignore'), wc[w]))
