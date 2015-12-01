#!/usr/bin/env python
# vim: set fileencoding=utf-8 fdm=marker :
"""
This module provides tools for **CZECH** normalisation of transcriptions, mainly for
those obtained from human transcribers.
"""

from __future__ import unicode_literals

import re

__all__ = ['normalise_text', 'exclude', 'exclude_by_dict']

_nonspeech_events = ['_SIL_', '_INHALE_', '_LAUGH_', '_EHM_HMM_', '_NOISE_', '_EXCLUDE_',]

for idx, ne in enumerate(_nonspeech_events):
    _nonspeech_events[idx] = (re.compile(r'((\b|\s){pat}(\b|\s))+'.format(pat=ne)), ' '+ne+' ')

# nonspeech event transcriptions {{{
_nonspeech_map = {
    '_SIL_': (
        '(SIL)',
        '(QUIET)',
        '(CLEARING)',
        '<SILENCE>',
        '[SIL]',
    ),
    '_INHALE_': (
        '(INHALE)',
        '(BREATH)',
        '(BREATHING)',
        '(SNIFFING)',
        '<INHALE>',
    ),
    '_LAUGH_': (
        '(LAUGH)',
        '(LAUGHING)',
        '<LAUGH>',
    ),
    '_EHM_HMM_': (
        '(EHM_HMM)',
        '(HESITATION)',
        '(HUM)',
        '<COUGH>',
        '<MOUTH>',
        '<EHM A>',
        '<EHM N>',
        '<EHM >',
        '<EHM>',
    ),
    '_NOISE_': (
        '(NOISE)',
        '(NOISES)',
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
        '(STATIC)',
        '(SCRAPE)',
        '(SQUEAK)',
        '(TVNOISE)',
        '<NOISE>',
        '[NOISE]',
        '[NOISE-PEAK]',
        '[NOISE-HIGH]',
        '[NOISE-LOW]',
        '//NOISE//',
    ),
    '_EXCLUDE_': (
        '(EXCLUDE)',
        '(PERSONAL)',
        '(VULGARISM)',
        '(UNINTELLIGIBLE)',
        '(UNINT)',
        '[UNINTELLIGIBLE]',
        '[BACKGROUND SPEECH]',
        '[BACKGROUND-SPEECH]',
        '[BACKGROUND_SPEECH]',
        '[BACKGROUND=SPEECH]',
    )
}
#}}}
_nonspeech_trl = dict()
for uscored, forms in _nonspeech_map.iteritems():
    for form in forms:
        _nonspeech_trl[form] = uscored

# substitutions {{{
_subst = [
          ('UNINTELLIGIBLE', '_EXCLUDE_'),
          ('UNINT', '_EXCLUDE_'),
          ('NOISE', '_EXCLUDE_'),
          ('BACKGROUND', '_EXCLUDE_'),
          ('SPEECH', '_EXCLUDE_'),
          ('ČL.', '_EXCLUDE_'),
          ('EL.', '_EXCLUDE_'),
          ('PÍSM.', '_EXCLUDE_'),
          ('ATD.', '_EXCLUDE_'),
          ('ING.', '_EXCLUDE_'),
          ('TZV.', '_EXCLUDE_'),
          ('ODST.', '_EXCLUDE_'),
          ('APOD.', '_EXCLUDE_'),
          ('DR.', '_EXCLUDE_'),
          ('O.S.Ř.', '_EXCLUDE_'),
          ('S.R.O.', '_EXCLUDE_'),
          ('S. R. O.', '_EXCLUDE_'),
          ('PROF.', '_EXCLUDE_'),
          ('DOC.', '_EXCLUDE_'),
          ('PS', '_EXCLUDE_'),
          ('6E', ' '), 
          ('AČAKOLIV', 'AČKOLIV'),
          ('ADRESTÁ', 'ADRESÁT'),
          ('ÁHOJ', 'AHOJ'),
          ('AKDEMII', 'AKADEMII'),
          ('AKORAT', 'AKORÁT'),
          ('ALIKOVANÉ', 'APLIKOVANÉ'),
          ('AMERIČEN', 'AMERIČAN'),
          ('AMFÓROVÁ', 'AMFOROVÁ'),
          ('ÁNO', 'ANO'),
          ('ANÓ', 'ANO'),
          ('AJPÍ', 'AJ PÍ'),
          ('APLIÓNU', 'AMPLIÓNU'),
          ('AUSTÁLIE', 'AUSTRÁLIE'),
          ('BARANDOV', 'BARRANDOV'),
          ('BĚŽÉ', 'BĚŽÍ'),
          ('BRATISLABY', 'BRATISLAVY'),
          ('BRNÉ', 'BRNĚ'),
          ('ČAPLINOVA', 'CHAPLINOVA'),
          ('CHAPLINO', 'CHAPLINOVO'),
          ('ČAPLINOVO', 'CHAPLINOVO'),
          ('ČEPLINOVO', 'CHAPLINOVO'),
          ('ČEPLINOVĚ', 'CHAPLINOVĚ'),
          ('CHCTE', 'CHCETE'),
          ('DEFICID', 'DEFICIT'),
          ('DEKUJI', 'DĚKUJI'),
          ('DĚLALÁ', 'DĚLALA'),
          ('DĚNNĚ', 'DENNĚ'),
          ('DENNNĚ', 'DENNĚ'),
          ('DIVADLÓ', 'DIVADLO'),
          ('DOMÁCÍCCH', 'DOMÁCÍCH'),
          ('DÓ', 'DO'),
          ('DVACETDVOJKOU', 'DVACET DVOJKOU'),
          ('EXPERIMENTYY', 'EXPERIMENTY'),
          ('EŠTĚ', 'JEŠTĚ'),
          ('FYZIKOLOGIE', 'FYZIOLOGIE'),
          ('GORADŽE', 'GORAŽDE'),
          ('HALO', 'HALÓ'),
          ('HELICHOVA', 'HELLICHOVA'),
          ('HLAVNIM', 'HLAVNÍM'),
          ('HVĚZDÁ', 'HVĚZDNÁ'),
          ('INICIATIVNU', 'INICIATIVU'),
          ('ÍPÉPAVLOVA', 'I P PAVLOVA'),
          ('Í PÉ PAVLOVA', 'I P PAVLOVA'),
          ('ÍPÉ PAVLOVA', 'I P PAVLOVA'),
          ('ÍPÉ PA PAVLOVA', 'I P PAVLOVA'),
          ('Í PÉ PAVLOVU', 'I P PAVLOVU'),
          ('ÍPÉ PAVLOVU', 'I P PAVLOVU'),
          ('Í PÉ PAVLOVY', 'I P PAVLOVY'),
          ('ÍPÉ PAVLOVY', 'I P PAVLOVY'),
          ('ÍPÉ', 'I P'),
          ('PÍPÉ', 'I P'),
          ('ISNTITUCE', 'INSTITUCE'),
          ('ISPEKCI', 'INSPEKCI'),
          ('JĚ', 'JE'),
          ('JESLTI', 'JESTLI'),
          ('JÉT', 'JET'),
          ('JINONICKA', 'JINONICKÁ'),
          ('JÍDZNÍ', 'JÍZDNÍ'),
          ('KABLOVNY', 'KABELOVNY'),
          ('KAŽDYM', 'KAŽDÝM'),
          ('KMOTŘEM', 'KMOTREM'),
          ('KOCOR', 'KOCOUR'),
          ('KONCEKRT', 'KONCERT'),
          ('KŘESŤANSÝCH', 'KŘESŤANSKÝCH'),
          ('KREVNÍCHH', 'KREVNÍCH'),
          ('KTOMU', 'K TOMU'),
          ('KUBÁŇSKÉ', 'KUBÁNSKÉ'),
          ('LECCOST', 'LECCOS'),
          ('LETŇÁN', 'LETŇAN'),
          ('LÍDÉ', 'LIDÉ'),
          ('LITERTŮŘE', 'LITERATŮŘE'),
          ('LITŇANSKÁ', 'LETŇANSKÁ'),
          ('MAJETKOVÝVH', 'MAJETKOVÝVCH'),
          ('MALOSTARNSKÉHO', 'MALOSTRANSKÉHO'),
          ('MEZIMÁRODNÍHO', 'MEZINÁRODNÍHO'),
          ('MÍSTOPŘESEDA', 'MÍSTOPŘEDSEDA'),
          ('MOŽNOT', 'MOŽNOST'),
          ('NÁHLÉDNUTÍ', 'NAHLÉDNUTÍ'),
          ('NAJASNÁ', 'NEJASNÁ'),
          ('NÁ', 'NA'),
          ('NÁDRAŽI', 'NÁDRAŽÍ'),
          ('NANAZAT', 'NAMAZAT'),
          ('NASCHLEDANOU', 'NA SHLEDANOU'),
          ('NASHLEDANOU', 'NA SHLEDANOU'),
          ('NASHLE', 'NA SHLE'),
          ('NEJČASĚJŠÍMI', 'NEJČASTĚJŠÍMI'),
          ('NĚKDĚ', 'NĚKDE'),
          ('NĚKDZ', 'NĚKDY'),
          ('NĚMECKKOU', 'NĚMECKOU'),
          ('NENATCHL', 'NENADCHL'),
          ('NEPRVE', 'NEJPRVE'),
          ('NEROZUMIM', 'NEROZUMÍM'),
          ('NESLYŠIM', 'NESLYŠÍM'),
          ('NEVIM', 'NEVÍM'),
          ('NEVYDŽEL', 'NEVYDRŽEL'),
          ('NIČIM', 'NIČÍM'),
          ('NMŮŽU', 'NEMŮŽU'),
          ('ŇÚTNOVA', 'NEWTONOVA'),
          ('ŇUTNOVÁ', 'NEWTONOVÁ'),
          ('ŇÚTNOVÁ', 'NEWTONOVÁ'),
          ('ŇUTNA', 'NEWTONA'),
          ('_NOISE_KAM', '_NOISE_ KAM'),
          ('(NOISE)KAM', '_NOISE_ KAM'),
          ('_NOISE_VONO', '_NOISE_ VONO'),
          ('(NOISE)VONO', '_NOISE_ VONO'),
          ('ODPOVĚDOSTI', 'ODPOVĚDNOSTI'),
          ('OKAY', 'OK'),
          ('OKEY', 'OK'),
          ('OPOMENTÝCH', 'OPOMENUTÝCH'),
          ('PACHATÉLŮ', 'PACHATELŮ'),
          ('PALMOVKÁ', 'PALMOVKA'),
          ('POCHATELŮ', 'PACHATELŮ'),
          ('PODIKATELSKÝ', 'PODNIKATELSKÝ'),
          ('POJĎMĚ', 'POJĎME'),
          ('POSLÚCHEJ', 'POSLŮCHEJ'),
          ('PRAHÁ', 'PRAHA'),
          ('PROSÍL', 'PROSIL'),
          ('PŘEVOLEBNÍ', 'PŘEDVOLEBNÍ'),
          ('PŘEVŠÍM', 'PŘEDVŠÍM'),
          ('PŘÍJMACÍ', 'PŘÍJÍMACÍ'),
          ('PŘÍJMANÉ', 'PŘÍJÍMANÉ'),
          ('PŘÍRUSTEK', 'PŘÍRŮSTEK'),
          ('PRAZÉ', 'PRAZE'),
          ('PROSIM', 'PROSÍM'),
          ('PROTESTNANTY', 'PROTESTANTY'),
          ('RADSOT', 'RADOST'),
          ('ROZHDODLA', 'ROZHODLA'),
          ('ROZSÁHLA', 'ROZSÁHLÁ'),
          ('S FLORENCE', 'Z FLORENCE'),
          ('SCHÁLIT', 'SCHVÁLIT'),
          ('SCHLEDANOU', 'SHLEDANOU'),
          ('ŠIKOVNNÝ', 'ŠIKOVNÝ'),
          ('SKOROVAL', 'SKÓROVAL'),
          ('SLOVENSŠTÍ', 'SLOVENŠTÍ'),
          ('SLYŠEEL', 'SLYŠEL'),
          ('SPOJEENÍ', 'SPOJENÍ'),
          ('SPOLECHEMIE', 'SPOLOCHEMIE'),
          ('SPORTNOVNÍMI', 'SPORTOVNÍMI'),
          ('SPUTIT', 'SPUSTIT'),
          ('ŠŠTVRT', 'ŠTVRT'),
          ('ŠTROSMAJEROVO', 'STROSSMAYEROVO'),
          ('STANDARTNĚ', 'STANDARDNĚ'),
          ('STEREOPTYPY', 'STEREOTYPY'),
          ('TAAKŽE', 'TAKŽE'),
          ('TAPATOVÝMI', 'TAPETOVÝMI'),
          ('TROHU', 'TROCHU'),
          ('TVDÝ', 'TVRDÝ'),
          ('UPEVIL', 'UPEVNIL'),
          ('ÚŘÁD', 'ÚŘAD'),
          ('UVĚĎMĚ', 'UVEĎMĚ'),
          ('VALDŠTEJSNKÁ', 'VALDŠTEJNSKÁ'),
          ('VŠAL', 'VŠAK'),
          ('VŠECHNOO', 'VŠECHNO'),
          ('VÝBEHU', 'VÝBĚHU'),
          ('VYPOŘÁDNÍ', 'VYPOŘÁDÁNÍ'),
          ('VYSOUPENÍ', 'VYSTOUPENÍ'),
          ('VYZVEDNÁVAT', 'VYZVEDÁVAT'),
          ('VZÁDLENOSTI', 'VZDÁLENOSTI'),
          ('VZDDĚLÁNÍ', 'VZDĚLÁNÍ'),
          ('VZTOUPÍ', 'VSTOUPÍ'),
          ('ZAJÁJENÍ', 'ZAHÁJENÍ'),
          ('ZALEŽÍ', 'ZÁLEŽÍ'),
          ('ZAVEDNÍ', 'ZAVEDENÍ'),
          ('ZASTÁVKŮ', 'ZASTÁVKU'),
          ('ZDRAVOTÍ', 'ZDRAVOTNÍ'),
          ('ZEA', 'ZE'),
          ('ZHODNOŤTĚ', 'ZHODNOŤTE'),
          ('ZPRACOVNÁNÍ', 'ZPRACOVÁNÍ'),
          ('ZROVNOPRÁVĚNÍ', 'ZROVNOPRÁVNĚNÍ'),
          ('ZTRÁŽNÍKY', 'STRÁŽNÍKY'),
          ('ZVLÁŠTÍ', 'ZVLÁŠTNÍ'),
          ('DOZADU_LAUGH_', 'DOZADU _LAUGH_'),
          ('DOZADU(LAUGH)', 'DOZADU (LAUGH)'),
          ('DOZADU<LAUGH>', 'DOZADU <LAUGH>'),
          ('OZVAT_LAUGH_', 'OZVAT _LAUGH_'),
          ('OZVAT(LAUGH)', 'OZVAT (LAUGH)'),
          ('OZVAT<LAUGH>', 'OZVAT <LAUGH>'),
          ('VENDY_LAUGH_', 'VENDY _LAUGH_'),
          ('VENDY(LAUGH)', 'VENDY (LAUGH)'),
          ('VENDY<LAUGH>', 'VENDY <LAUGH>'),
          ('FŔST', '_EXCLUDE_'),
          ('BRA', '_EXCLUDE_'),
          ('ALÉÉ', 'ALÉ'),
          ('DALĚÍ', 'DALŠÍ'),
          ('ANKTRARTIDA', 'ANTARKTIDA'),
          ('MALOSTRANSKÁ ALE BUĎ JIŽ DALŠÍ', 'MALOSTRANSKÁ ALE BUDIŽ DALŠÍ'),
          ('DEVEDASÁT', 'DEVEDESÁT'),
          ('DLOUHAU', 'DLOUHOU'),
          ('DLÓHÓ', 'DLÓHO'),
          ('DNESKÁ', 'DNESKA'),
          ('DVACETSEDUM', 'DVACET SEDUM'),
          ('DVACETTŘI', 'DVACET TŘI'),
          ('DVACETČTYRY', 'DVACET ČTYRY'),
          ('DVACETŠEST', 'DVACET ŠEST'),
          ('DVACÁTÉHOOSMÉHO', 'DVACÁTÉHO OSMÉHO'),
          ('DVACÁTÉHOSMÉHO', 'DVACÁTÉHO OSMÉHO'),
          ('DVACÁTÝHOŠESTÝHO', 'DVACÁTÝHO ŠESTÝHO'),
          ('DVATISÍCETŘINÁCT', 'DVATISÍCE TŘINÁCT'),
          ('DVĚSTĚDVOJKA', 'DVĚSTĚ DVOJKA'),
          ('DVĚSTĚPADESÁT', 'DVĚSTĚ PADESÁT'),
          ('DĚKUJÚ', 'DĚKUJŮ'),
          ('ERROR', 'EROR'),
          ('HŮŮ', 'HŮ'),
          ('JÉÉ', 'JÉ'),
          ('JÉŽIŠ', 'JÉŽÍŠ'),
          ('KRČSKA', 'KRČSKÁ'),
          ('KVASNICÁ', 'KVASNICKÁ'),
          ('NADRAŽÍ', 'NÁDRAŽÍ'),
          ('NÉÉ', 'NÉ'),
          ('POLIKLANIKA', 'POLIKLINIKA'),
          ('POLIKLLINIKY', 'POLIKLINIKY'),
          ('POSLEDNÉHO', 'POSLEDNÍHO'),
          ('STODVACET', 'STO DVACET'),
          ('STODVOJKA', 'STO DVOJKA'),
          ('STOJEDNA', 'STO JEDNA'),
          ('STOSEDMDESÁT', 'STO SEDMDESÁT'),
          ('STOŠEDESÁTJEDNA', 'STO ŠEDESÁT JEDNA'),
          ('TUOLEVOVY', 'TUPOLEVOVY'),
          ('VUNIČOVĚ', 'V UNIČOVĚ'),
          ('ČTYŘICETŠET', 'ČTYŘICET ŠET'),
          ('ZA ANDĚLA', 'Z ANDĚLA'),
          ('ANTŔT', 'ANTRT'),
          ('MALOSTARNSKÉHO', 'MALOSTRANSKÉHO'),
          ('POLIKLLINIKY', 'POLIKLINIKY'),
          ('JSEMSE', 'JSEM SE'),
          ('%', 'PROCENT'),
          ('JEDNA /', 'JEDNA LOMENO'),
          ('DVA /', 'DVA LOMENO'),
          ('TŘI /', 'TŘI LOMENO'),
          ('ČTYŘI /', 'ČTYŘI LOMENO'),
          ('PĚT /', 'PĚT LOMENO'),
          ('ŠEST /', 'ŠEST LOMENO'),
          ('SEDM /', 'SEDM LOMENO'),
          ('OSM /', 'OSM LOMENO'),
          ('DĚVET /', 'DEVĚT LOMENO'),
          ('DESET /', 'DESET LOMENO'),
          ('SB.', 'SBÍRKY'),
          ]
#}}}
for idx, tup in enumerate(_subst):
    pat, sub = tup
    _subst[idx] = (re.compile(r'(^|\s){pat}($|\s)'.format(pat=pat)), ' '+sub+' ')
    # alternative and probably better use this in the future, but must be tested!
    # _subst[idx] = (re.compile(r'\b{pat}\b'.format(pat=pat)), ' '+sub+' ', flags=re.UNICODE)

# hesitation expressions {{{
_hesitation = ['AAAA', 'AAA', 'AA', 'AAH', 'A-', "-AH-", "AH-", "AH.", "AH",
               "AHH", "AHHH", "AHMA", "AHM", "ANH", "ARA", "-AR",
               "AR-", "-AR", "ARRH", "AW", "EA-", "-EAR", "-EECH", "\"EECH\"",
               "-EEP", "-E", "E-", "EH", "EM", "--", "ER", "ERM", "ERR",
               "ERRM", "EX-", "F-", "HM", "HMM", "HMMM", "-HO", "HUH", "HU",
               "HUM", "HUMM", "HUMN", "HUMN", "HUMPH", "HUP", "HUU", "-",
               "MM", "MMHMM", "MMM", "NAH", "OHH", "OH", "SH", "UHHH",
               "UHH", "UHM", "UH'", "UH", "UHUH", "UHUM", "UMH", "UMM", "UMN",
               "UM", "URM", "URUH", "UUH", "ARRH", "AW", "EM", "ERM", "ERR",
               "ERRM", "HUMN", "UM", "UMN", "URM", "AH", "ER", "ERM", "HUH",
               "HUMPH", "HUMN", "HUM", "HU", "SH", "UH", "UHUM", "UM", "UMH",
               "URUH", "MMMM", "MMM", "OHM", "UMMM"]
# }}}
for idx, word in enumerate(_hesitation):
    _hesitation[idx] = re.compile(r'(^|\s){word}($|\s)'.format(word=word))

_more_spaces = re.compile(r'\s{2,}')
_sure_punct_rx = re.compile(r'[.?!",\t]')
_parenthesized_rx = re.compile(r'\(+([^)]*)\)+')
_bracketized_rx = re.compile(r'\[+([^\[]*)\]+')


def normalise_text(text):
    """
    Normalises the transcription.  This is the main function of this module.
    """
    text = text.strip().upper()

    # Do dictionary substitutions
    for pat, sub in _subst:
        text = pat.sub(sub, text)

    text = _sure_punct_rx.sub(' ', text)

    # Do dictionary substitutions after removing puctuation again.
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
    if '(' in text or '<' in text or '[' in text or '/' in text:
        text = _parenthesized_rx.sub(r' (\1) ', text)
        text = _bracketized_rx.sub(r' (\1) ', text)
        
        for parenized, uscored in _nonspeech_trl.iteritems():
            text = text.replace(parenized, uscored)
        
        text = _more_spaces.sub(' ', text.strip())

    # remove duplicate non-speech events
    for pat, sub in _nonspeech_events:
        text = pat.sub(sub, text)
    text = _more_spaces.sub(' ', text).strip()

    for char in '^':
        text = text.replace(char, '')

    return text

_excluded_characters = set(['\n', '=', '-', '*', '+', '~', ':', '&', '/', '§', "''", '|', '_', '$',
                           '(', ')', '[', ']', '{', '}', '<', '>', 
                           '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'Ŕ'])

def exclude_asr(text):
    """
    This function is used for determining whether the transcription can be used for training ASR.

    Determines whether `text' is not good enough and should be excluded.
    "Good enough" is defined as containing none of `_excluded_characters' and being
    longer than one word.
    """
    if '_EXCLUDE_' in text:
        return True

    if text in ['_SIL_', ]:
        return True

    if text in ['_NOISE_', '_EHM_HMM_', '_INHALE_', '_LAUGH_']:
        return False

    # allow for sentences with these non-speech events if mixed with text
    for s in ['_NOISE_', '_INHALE_', '_LAUGH_']:
        text = text.replace(s,'')

    for char in _excluded_characters:
        if char in text:
            return True
    if '_' in text:
        return True

    if len(text) < 2:
        return True

    return False

def exclude_lm(text):
    """
    This function is used for determining whether the transcription can be used for Language Modeling.

    Determines whether `text' is not good enough and should be excluded.
    "Good enough" is defined as containing none of `_excluded_characters' and being
    longer than one word.
    """

    if '_EXCLUDE_' in text:
        return True

    for char in _excluded_characters:
        if char in text:
            return True

    return False

def exclude_slu(text):
    """
    This function is used for determining whether the transcription can be used for training Spoken Language Understanding.
    """
    return exclude_lm(text)

def exclude_by_dict(text, known_words):
    """
    Determines whether text is not good enough and should be excluded.

    "Good enough" is defined as having all its words present in the
    `known_words' collection."""
    return not all(map(lambda word: word in known_words, text.split()))
