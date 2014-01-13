#!/usr/bin/env python
# vim: set fileencoding=utf-8 fdm=marker :
"""
This module provides tools for **CZECH** normalisation of transcriptions, mainly for
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
        '(CLEARING)',
        '<SILENCE>',
    ),
    '_INHALE_': (
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
    ),
    '_EXCLUDE_': (
        '(UNINTELLIGIBLE)',
        '(UNINT)',
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
          ('JESLTI', 'JESTLI'),
          ('NMŮŽU', 'NEMŮŽU'),
          ('_NOISE_KAM', '_NOISE_ KAM'),
          ('(NOISE)KAM', '_NOISE_ KAM'),
          ('_NOISE_VONO', '_NOISE_ VONO'),
          ('(NOISE)VONO', '_NOISE_ VONO'),
          ('6E', ' '),
          ('OKEY', 'OK'),
          ('OKAY', 'OK'),
          ('ÁHOJ', 'AHOJ'),
          ('ÁNO', 'ANO'),
          ('BARANDOV', 'BARRANDOV'),
          ('ZEA', 'ZE'),
          ('LITŇANSKÁ', 'LETŇANSKÁ'),
          ('ANÓ', 'ANO'),
          ('NEVIM', 'NEVÍM'),
          ('DEKUJI', 'DĚKUJI'),
          ('SCHLEDANOU', 'SHLEDANOU'),
          ('NASHLEDANOU', 'NA SHLEDANOU'),
          ('NEROZUMIM', 'NEROZUMÍM'),
          ('ADRESTÁ', 'ADRESÁT'),
          ('KAŽDYM', 'KAŽDÝM'),
          ('ALIKOVANÉ', 'APLIKOVANÉ'),
          ('AMERIČEN', 'AMERIČAN'),
          ('APLIÓNU', 'AMPLIÓNU'),
          ('AUSTÁLIE', 'AUSTRÁLIE'),
          ('AČAKOLIV', 'AČKOLIV'),
          ('BRATISLABY', 'BRATISLAVY'),
          ('CHCTE', 'CHCETE'),
          ('DEFICID', 'DEFICIT'),
          ('DOMÁCÍCCH', 'DOMÁCÍCH'),
          ('DĚNNĚ', 'DENNĚ'),
          ('EXPERIMENTYY', 'EXPERIMENTY'),
          ('FYZIKOLOGIE', 'FYZIOLOGIE'),
          ('GORADŽE', 'GORAŽDE'),
          ('HVĚZDÁ', 'HVĚZDNÁ'),
          ('INICIATIVNU', 'INICIATIVU'),
          ('ISNTITUCE', 'INSTITUCE'),
          ('ISPEKCI', 'INSPEKCI'),
          ('JÍDZNÍ', 'JÍZDNÍ'),
          ('JĚ', 'JE'),
          ('KABLOVNY', 'KABELOVNY'),
          ('KMOTŘEM', 'KMOTREM'),
          ('KTOMU', 'K TOMU'),
          ('KŘESŤANSÝCH', 'KŘESŤANSKÝCH'),
          ('LECCOST', 'LECCOS'),
          ('LITERTŮŘE', 'LITERATŮŘE'),
          ('LÍDÉ', 'LIDÉ'),
          ('MAJETKOVÝVH', 'MAJETKOVÝVCH'),
          ('MEZIMÁRODNÍHO', 'MEZINÁRODNÍHO'),
          ('MOŽNOT', 'MOŽNOST'),
          ('MÍSTOPŘESEDA', 'MÍSTOPŘEDSEDA'),
          ('NAJASNÁ', 'NEJASNÁ'),
          ('NANAZAT', 'NAMAZAT'),
          ('NEJČASĚJŠÍMI', 'NEJČASTĚJŠÍMI'),
          ('NENATCHL', 'NENADCHL'),
          ('NEPRVE', 'NEJPRVE'),
          ('NESLYŠIM', 'NESLYŠÍM'),
          ('NEVYDŽEL', 'NEVYDRŽEL'),
          ('NÁHLÉDNUTÍ', 'NAHLÉDNUTÍ'),
          ('NĚMECKKOU', 'NĚMECKOU'),
          ('ODPOVĚDOSTI', 'ODPOVĚDNOSTI'),
          ('OPOMENTÝCH', 'OPOMENUTÝCH'),
          ('PACHATÉLŮ', 'PACHATELŮ'),
          ('POCHATELŮ', 'PACHATELŮ'),
          ('PODIKATELSKÝ', 'PODNIKATELSKÝ'),
          ('PROTESTNANTY', 'PROTESTANTY'),
          ('PŘEVOLEBNÍ', 'PŘEDVOLEBNÍ'),
          ('PŘEVŠÍM', 'PŘEDVŠÍM'),
          ('PŘÍJMACÍ', 'PŘÍJÍMACÍ'),
          ('PŘÍJMANÉ', 'PŘÍJÍMANÉ'),
          ('PŘÍRUSTEK', 'PŘÍRŮSTEK'),
          ('RADSOT', 'RADOST'),
          ('ROZHDODLA', 'ROZHODLA'),
          ('ROZSÁHLA', 'ROZSÁHLÁ'),
          ('SCHÁLIT', 'SCHVÁLIT'),
          ('SKOROVAL', 'SKÓROVAL'),
          ('SLOVENSŠTÍ', 'SLOVENŠTÍ'),
          ('SPOLECHEMIE', 'SPOLOCHEMIE'),
          ('SPORTNOVNÍMI', 'SPORTOVNÍMI'),
          ('STANDARTNĚ', 'STANDARDNĚ'),
          ('STEREOPTYPY', 'STEREOTYPY'),
          ('TAPATOVÝMI', 'TAPETOVÝMI'),
          ('TVDÝ', 'TVRDÝ'),
          ('UPEVIL', 'UPEVNIL'),
          ('UVĚĎMĚ', 'UVEĎMĚ'),
          ('VYPOŘÁDNÍ', 'VYPOŘÁDÁNÍ'),
          ('VYSOUPENÍ', 'VYSTOUPENÍ'),
          ('VZDDĚLÁNÍ', 'VZDĚLÁNÍ'),
          ('VZTOUPÍ', 'VSTOUPÍ'),
          ('VZÁDLENOSTI', 'VZDÁLENOSTI'),
          ('VÝBEHU', 'VÝBĚHU'),
          ('VŠAL', 'VŠAK'),
          ('ZAJÁJENÍ', 'ZAHÁJENÍ'),
          ('ZALEŽÍ', 'ZÁLEŽÍ'),
          ('ZAVEDNÍ', 'ZAVEDENÍ'),
          ('ZDRAVOTÍ', 'ZDRAVOTNÍ'),
          ('ZHODNOŤTĚ', 'ZHODNOŤTE'),
          ('ZPRACOVNÁNÍ', 'ZPRACOVÁNÍ'),
          ('ZROVNOPRÁVĚNÍ', 'ZROVNOPRÁVNĚNÍ'),
          ('ZTRÁŽNÍKY', 'STRÁŽNÍKY'),
          ('ZVLÁŠTÍ', 'ZVLÁŠTNÍ'),
          ('ÚŘÁD', 'ÚŘAD'),
          ('AKDEMII', 'AKADEMII'),
          ('AKORAT', 'AKORÁT'),
          ('BĚŽÉ', 'BĚŽÍ'),
          ('CHCTE', 'CHCETE'),
          ('DENNNĚ', 'DENNĚ'),
          ('DĚLALÁ', 'DĚLALA'),
          ('KOCOR', 'KOCOUR'),
          ('KONCEKRT', 'KONCERT'),
          ('KREVNÍCHH', 'KREVNÍCH'),
          ('NĚKDZ', 'NĚKDY'),
          ('NĚKDĚ', 'NĚKDE'),
          ('POJĎMĚ', 'POJĎME'),
          ('POSLÚCHEJ', 'POSLŮCHEJ'),
          ('SLYŠEEL', 'SLYŠEL'),
          ('SPOJEENÍ', 'SPOJENÍ'),
          ('SPUTIT', 'SPUSTIT'),
          ('TAAKŽE', 'TAKŽE'),
          ('TROHU', 'TROCHU'),
          ('VALDŠTEJSNKÁ', 'VALDŠTEJNSKÁ'),
          ('VYZVEDNÁVAT', 'VYZVEDÁVAT'),
          ('VŠECHNOO', 'VŠECHNO'),
          ('ŠIKOVNNÝ', 'ŠIKOVNÝ'),
          ('ŠŠTVRT', 'ŠTVRT'),
          ('KUBÁŇSKÉ', 'KUBÁNSKÉ'),
          ('Í PÉ PAVLOVA', 'I P PAVLOVA'),
          ('Í PÉ PAVLOVY', 'I P PAVLOVY'),
          ('Í PÉ PAVLOVU', 'I P PAVLOVU'),
          ('ÍPÉ PAVLOVA', 'I P PAVLOVA'),
          ('ÍPÉ PAVLOVY', 'I P PAVLOVY'),
          ('ÍPÉ PAVLOVU', 'I P PAVLOVU'),
          ('ČAPLINOVO', 'CHAPLINOVO'),
          ('ČAPLINOVA', 'CHAPLINOVA'),
          ('ČEPLINOVĚ', 'CHAPLINOVĚ'),
          ('DIVADLÓ', 'DIVADLO'),
          ('LETŇÁN', 'LETŇAN'),
          ('JÉT', 'JET'),
          ('NÁ', 'NA'),
          ('AMFÓROVÁ', 'AMFOROVÁ'),
          ]
#}}}
for idx, tup in enumerate(_subst):
    pat, sub = tup
    _subst[idx] = (re.compile(r'(^|\s){pat}($|\s)'.format(pat=pat)), ' '+sub+' ')

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
    if '(' in text or '<' in text:
        text = _parenthesized_rx.sub(r' (\1) ', text)
        for parenized, uscored in _nonspeech_trl.iteritems():
            text = text.replace(parenized, uscored)
        text = _more_spaces.sub(' ', text.strip())

    for char in '^':
        text = text.replace(char, '')

    return text
#}}}


def exclude_asr(text):
    """
    This function is used for determining whether the transcription can be used for training ASR.

    Determines whether `text' is not good enough and should be excluded.
    "Good enough" is defined as containing none of `_excluded_characters' and being
    longer than one word.
    """
    if text in ['_NOISE_', '_EHM_HMM_', '_INHALE_', '_LAUGH_']:
        return False

    for char in _excluded_characters:
        if char in text:
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

    if text.find('_EXCLUDE_') >= 0:
        return True

    for char in _excluded_characters:
        if char in text  and char not in ['_']:
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
