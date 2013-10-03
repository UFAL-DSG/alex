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
        '(SCRAPE)',
        '(SQUEAK)',
        '(TVNOISE)',
        '<NOISE>',
    )
}
#}}}
_nonspeech_trl = dict()
for uscored, forms in _nonspeech_map.iteritems():
    for form in forms:
        _nonspeech_trl[form] = uscored


# substitutions {{{
_subst = [('JESLTI', 'JESTLI'),
          ('NMŮŽU', 'NEMŮŽU'),
          ('_NOISE_KAM', '_NOISE_ KAM'),
          ('(NOISE)KAM', '_NOISE_ KAM'),
          ('6E', ' '),
          ('OKEY', 'OK'),
          ('OKAY', 'OK'),
          ('ÁHOJ', 'AHOJ'),
          ('ÁNO', 'ANO'),
          ('BARANDOV', 'BARRANDOV'),
          ('ZEA', 'ZE'),
          ('LITŇANSKÁ', 'LETŇANSKÁ'),
          ('ANÓ', 'ANO'),
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


def normalise_text(text):
    """
    Normalises the transcription.  This is the main function of this module.
    """
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

    # remove signs of (1) incorrect pronunciation, (2) stuttering, (3) bargin
    # return text.translate(None, '*+~')
    for char in '*+~':
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
