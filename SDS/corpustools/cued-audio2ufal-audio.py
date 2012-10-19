#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import glob
import os.path
import argparse
import xml.dom.minidom
import shutil
import collections

import __init__

from SDS.utils.various import flatten, get_text_from_xml_node

"""
This program process CUED call log files and copies all audio into a destination directory.
It also extracts transcriptions from the log files and saves them alongside the copied wavs.

It scans for 'user-transcription.norm.xml' to extract transcriptions and names of wave files.

"""

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

hesitation = ['AAAA', 'AAA', 'AA', 'AAH', 'A-', "-AH-", "AH-", "AH.", "AH", "AHA", "AHH", "AHHH", "AHMA", "AHM", "ANH", "ARA", "-AR", "AR-",
              "-AR", "ARRH", "AW", "EA-", "-EAR", "-EECH", "\"EECH\"", "-EEP", "-E", "E-", "EH", "EM", "--", "ER", "ERM", "ERR", "ERRM", "EX-",
              "F-", "HM", "HMM", "HMMM", "-HO", "HUH", "HU", "-", "HUM", "HUMM", "HUMN", "HUMN", "HUMPH", "HUP", "HUU", "MM", "MMHMM", "MMM", "NAH",
              "OHH", "OH", "SH", "--", "UHHH", "UHH", "UHM", "UH'", "UH", "UHUH", "UHUM", "UMH", "UMM", "UMN", "UM", "URM", "URUH", "UUH", "ARRH",
              "AW", "EM", "ERM", "ERR", "ERRM", "HUMN", "UM", "UMN", "URM", "AH", "ER", "ERM", "HUH", "HUMPH", "HUMN", "HUM", "HU", "SH", "UH",
              "UHUM", "UM", "UMH", "URUH", "MMMM", "MMM", "OHM", "UMMM"]

excluded_caracters = ['-', '+', '(', ')', '[', ']', '{', '}', '<', '>', '0',
                      '1', '2', '3', '4', '5', '6', '7', '8', '9']


def normalization(text):
    t = text.strip().upper()

    t = t.strip().replace(
        '    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
    for a, b in [('.', ' '), ('?', ' '), ('!', ' '), ('"', ' '), (',', ' '), ('_', ' '), ]:
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


def exclude(text):
    for c in excluded_caracters:
        if c in text:
            return True
    if len(text) < 2:
        return True

    return False


d = collections.defaultdict(int)


def update_dict(text):
    t = text.split()

    for w in t:
        d[w] += 1


def save_transcription(transcription_file_name, transcription):
    f = open(transcription_file_name, 'w+')
    f.write(transcription.encode('ascii', 'ignore'))
    f.close()


def extract_wavs_trns(file, outdir, waves_mapping, verbose):
    """Extracts wavs and their transcriptions from the provided CUED call log file."""

    # load the file
    doc = xml.dom.minidom.parse(file)
    els = doc.getElementsByTagName("userturn")

    size = 0
    for el in els:
        print '-' * 120

        transcription = el.getElementsByTagName("transcription")
        audio = el.getElementsByTagName("rec")

        if len(transcription) != 1 or len(audio) != 1:
            # skip this node, it contains multiple elements of either transcription or audio.
            continue

        audio = audio[0].getAttribute('fname').strip()
        transcription = get_text_from_xml_node(
            transcription[0]).encode('ascii', 'ignore')
        if verbose:
            print " # f:", audio, "t:", transcription

        transcription = normalization(transcription)
        if verbose:
            print " # f:", audio, "t:", transcription

        if exclude(transcription):
            continue

        update_dict(transcription)
        if verbose:
            print " # f:", audio, "t:", transcription

        dir = os.path.dirname(file)

        audio_file_name = waves_mapping[audio]
        transcription_file_name = os.path.join(outdir, audio + '.trn')

        try:
            size += os.path.getsize(audio_file_name)
            shutil.copy2(audio_file_name, outdir)
            save_transcription(transcription_file_name, transcription)
        except OSError:
            print "Missing audio file:", audio_file_name

    return size


def get_waves_mapping(indir_audio):
    mapping = {}

    files = []
    files.append(glob.glob(os.path.join(indir_audio, '*', '*.wav')))
    files.append(glob.glob(os.path.join(indir_audio, '*', '*', '*.wav')))
    files.append(glob.glob(os.path.join(indir_audio, '*', '*', '*', '*.wav')))
    files.append(
        glob.glob(os.path.join(indir_audio, '*', '*', '*', '*', '*.wav')))
    files.append(glob.glob(
        os.path.join(indir_audio, '*', '*', '*', '*', '*', '*.wav')))

    files = flatten(files)

    for f in files:
        mapping[os.path.basename(f)] = f

    return mapping


def convert(indir, indir_audio, outdir, verbose):
    # get all wave files
    waves_mapping = get_waves_mapping(indir_audio)

    # get all transcriptions
    files = []
    files.append(
        glob.glob(os.path.join(indir, '*', 'user-transcription.norm.xml')))
    files.append(glob.glob(
        os.path.join(indir, '*', '*', 'user-transcription.norm.xml')))
    files.append(glob.glob(
        os.path.join(indir, '*', '*', '*', 'user-transcription.norm.xml')))
    files.append(glob.glob(os.path.join(
        indir, '*', '*', '*', '*', 'user-transcription.norm.xml')))
    files.append(glob.glob(os.path.join(
        indir, '*', '*', '*', '*', '*', 'user-transcription.norm.xml')))

    files = flatten(files)

    if len(files) < 2:
        # search for un normalised transcriptions
        print "Normalised transriptions were NOT found. Using unnormalised transcriptions!"

        files.append(
            glob.glob(os.path.join(indir, '*', 'user-transcription.xml')))
        files.append(glob.glob(
            os.path.join(indir, '*', '*', 'user-transcription.xml')))
        files.append(glob.glob(
            os.path.join(indir, '*', '*', '*', 'user-transcription.xml')))
        files.append(glob.glob(os.path.join(
            indir, '*', '*', '*', '*', 'user-transcription.xml')))
        files.append(glob.glob(os.path.join(
            indir, '*', '*', '*', '*', '*', 'user-transcription.xml')))

        files = flatten(files)

    size = 0
    for f in files:

        if verbose:
            print "Processing call log file: ", f

            size += extract_wavs_trns(f, outdir, waves_mapping, verbose)

    print "Size of copied audio data:", size

    sec = size / (16000 * 2)
    hour = sec / 3600.0

    print "Length of audio data in hours (for 16kHz 16b WAVs):", hour

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      This program process CUED call log files and copies all audio into a destination directory.
      It also extracts transcriptions from the log files and saves them alongside the copied wavs.

      It scans for 'user-transcription.norm.xml' to extract transcriptions and names of wave files.

      """)

    parser.add_argument('indir', action="store",
                        help='an input directory with CUED call log files')
    parser.add_argument('indir_audio', action="store",
                        help='an input directory with CUED audio files')
    parser.add_argument('outdir', action="store",
                        help='an output directory for files with audio and their transcription')
    parser.add_argument(
        '-v', action="store_true", default=False, dest="verbose",
        help='set verbose oputput')

    args = parser.parse_args()

    convert(args.indir, args.indir_audio, args.outdir, args.verbose)

    f = open('word_list', 'w')
    for w in sorted(d.keys()):
        f.write("%s\t%d" % (w.encode('ascii', 'ignore'), d[w]))
        f.write('\n')
    f.close()
