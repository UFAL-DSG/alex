#!/usr/bin/env python
# vim: set fileencoding=utf-8 fdm=marker :
"""
This module provides tools for **ENGLISH** normalisation of transcriptions, mainly for
those obtained from human transcribers.
"""

from __future__ import unicode_literals

import re

__all__ = ['normalise_text', 'exclude', 'exclude_by_dict']

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
        '(STATIC)',
        '(SQUEAK)',
        '(TVNOISE)')
}
#}}}
_nonspeech_trl = dict()
for uscored, forms in _nonspeech_map.iteritems():
    for form in forms:
        _nonspeech_trl[form] = uscored


# substitutions {{{
_subst = [('GOOD-BYE', 'GOODBYE'),
          ('GOOD BYE', 'GOODBYE'),
          ('BYE-BYE', 'BYE BYE'),
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
          ('ADDENBROOKE\'S\'',  'ADDENBROOKE\'S'),
          ('ADDENBROOKES\'',  'ADDENBROOKE\'S'),
          ('ADDENBROOKES\'A',  'ADDENBROOKE\'S'),
          ('ADDENBROOKE\'S\'A', 'ADDENBROOKE\'S'),
          ('ADDENBROOKE\'S\'S', 'ADDENBROOKE\'S'),
          ('ADDNEBROOKE\'S',  'ADDENBROOKE\'S'),
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
          ('CASTLE HILL\'', 'CASTLEHILL\'S'),
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
          ('WE\'', 'WE'),
          ('THEY\'', 'THEY'),
          ('YOU\'', 'YOU'),
          ('QUEENS\'', 'QUEEN\'S'),
          ('\'KAY', 'KAY'),
          ('AREA`', 'AREA'),
          ('APUB', 'A PUB'),
          ('CCENTRAL', 'CENTRAL'),
          ('FFSION', 'FUSION'),
          ('FOIR', 'FOR'),
	  ('KINKGSHEDGES', 'KINGSHEDGES'),
          ('MEXIAN', 'MEXICAN'),
          ('STREE', 'STREET'),
          ('INT HE', 'IN THE'),
          ('INTERNNATIONAL', 'INTERNATIONAL'), 
          ('RESTAURAT', 'RESTAURANT'), 
          ('THA\'S', 'THAT\'S'), 
          ('STANDARAD', 'STANDARD'),
          ('TRUMPINTON', 'TRUMPINGTON'),
          ('INTERNATION', 'INTERNATIONAL'), 
          ('NEWHAM', 'NEWNHAM'),
          ('VENE', 'VENUE'), 
          ('ROMSY', 'ROMSEY'),
          ]
#}}}
for idx, tup in enumerate(_subst):
    pat, sub = tup
    _subst[idx] = (re.compile(r'(^|\s){pat}($|\s)'.format(pat=pat)), ' '+sub+' ')

# hesitation expressions {{{
_hesitation = ['AAAA', 'AAA', 'AA', 'AAH', 'A-', "-AH-", "AH-", "AH.", "AH",
               "AHA", "AHH", "AHHH", "AHMA", "AHM", "ANH", "ARA", "-AR",
               "AR-", "-AR", "ARRH", "AW", "EA-", "-EAR", "-EECH", "\"EECH\"",
               "-EEP", "-E", "E-", "EH", "EM", "--", "ER", "ERM", "ERR",
               "ERRM", "EX-", "F-", "HM", "HMM", "HMMM", "-HO", "HUH", "HU",
               "HUM", "HUMM", "HUMN", "HUMN", "HUMPH", "HUP", "HUU", "-",
               "MM", "MMHMM", "MMM", "NAH", "OHH", "OH", "SH", "UHHH",
               "UHH", "UHM", "UH'", "UH", "UHUH", "UHUM", "UMH", "UMM", "UMN",
               "UM", "URM", "URUH", "UUH", "ARRH", "AW", "EM", "ERM", "ERR",
               "ERRM", "HUMN", "UM", "UMN", "URM", "AH", "ER", "ERM", "HUH",
               "HUMPH", "HUMN", "HUM", "HU", "SH", "UH", "UHUM", "UM", "UMH",
               "URUH", "MMMM", "MMM", "OHM", "UMMM", "MHMM"]
# }}}
for idx, word in enumerate(_hesitation):
    _hesitation[idx] = re.compile(r'(^|\s){word}($|\s)'.format(word=word))

_excluded_characters = ['_', '=', '-', '*', '+', '~', '(', ')', '[', ']', '{', '}', '<', '>', 
                        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

_more_spaces = re.compile(r'\s{2,}')
_sure_punct_rx = re.compile(r'[.?!",_]')
_parenthesized_rx = re.compile(r'\(+([^)]*)\)+')


def normalise_text(text):
    """
    Normalises the transcription.  This is the main function of this module.
    """
#{{{
    text = _sure_punct_rx.sub(' ', text)
    text = text.strip().upper()

    # Do dictionary substitutions.
    for pat, sub in _subst:
        text = pat.sub(sub, text)
    for word in _hesitation:
        text = word.sub(' (HESITATION) ', text)
    text = _more_spaces.sub(' ', text).strip()
    
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

    for char in '^':
        text = text.replace(char, '')

    return text
#}}}


def exclude(text):
    """
    Determines whether `text' is not good enough and should be excluded. "Good
    enough" is defined as containing none of `_excluded_characters' and being
    longer than one word.

    """
#{{{
    if text in ['_NOISE_', '_EHM_HMM_', '_SIL_', '_INHALE_', '_LAUGH_']:
	return False
    
    for char in _excluded_characters:
        if char in text:
            return True
    if len(text) < 2:
        return True

    return False
#}}}


def exclude_by_dict(text, known_words):
    """
    Determines whether text is not good enough and should be excluded.

    "Good enough" is defined as having all its words present in the
    `known_words' collection."""
    return not all(map(lambda word: word in known_words, text.split()))
