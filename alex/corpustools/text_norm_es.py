#!/usr/bin/env python
# vim: set fileencoding=utf-8 fdm=marker :
"""
This module provides tools for **ENGLISH** normalisation of transcriptions, mainly for
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
        '(SILENCE)',
        '(QUIET)',
        '(CLEARING)',
        '<SILENCE>',
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
    ),
    '_EXCLUDE_': (
        '(EXCLUDE)',
        '(PERSONAL)',
        '(VULGARISM)',
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
          ('_EXCLUDE_', '_EXCLUDE_'),
          ('ACUESTATE', 'ACUÉSTATE'),
          ('ALÓ', 'HALÓ'),
          ('AYUDAME', 'AYÚDAME'),
          ('BIOLOGIA', 'BIOLOGÍA'),
          ('CIENTIFICOS', 'CIENTÍFICOS'),
          ('DEMAS', 'DEMÁS'),
          ('FISCALIA', 'FISCALÍA'),
          ('GANACIA', 'GANANCIA'),
          ('GARABOA', 'GARAGOA'),
          ('INJUSTSICIA', 'INJUSTICIA'),
          ('INMANULADA', 'INMACULADA'),
          ('UDSTED', 'USTED'),
#          ('', ''),
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
               "MM", "MMHMM", "MMM", "NAH", "OHH", "OH", "SH", "UHHH", "EMMM"
               "UHH", "UHM", "UH'", "UH", "UHUH", "UHUM", "UMH", "UMM", "UMN",
               "UM", "URM", "URUH", "UUH", "ARRH", "AW", "EM", "ERM", "ERR",
               "ERRM", "HUMN", "UM", "UMN", "URM", "AH", "ER", "ERM", "HUH",
               "HUMPH", "HUMN", "HUM", "HU", "SH", "UH", "UHUM", "UM", "UMH",
               "URUH", "MMMM", "MMM", "OHM", "UMMM", "MHMM", "EMPH", "HMPH",
               "UGH", "UHH", "UMMMMM", "SHH", "OOH", ]
# }}}
for idx, word in enumerate(_hesitation):
    _hesitation[idx] = re.compile(r'(^|\s){word}($|\s)'.format(word=word))

_more_spaces = re.compile(r'\s{2,}')
_sure_punct_rx = re.compile(r'[.?!",_\n]')
_parenthesized_rx = re.compile(r'\(+([^)]*)\)+')


def normalise_text(text):
    """
    Normalises the transcription.  This is the main function of this module.
    """
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

    # remove duplicate non-speech events
    for pat, sub in _nonspeech_events:
        text = pat.sub(sub, text)
    text = _more_spaces.sub(' ', text).strip()

    for char in '^':
        text = text.replace(char, '')

    return text

_excluded_characters = set(['\n', '=', '-', '*', '+', '~', '(', ')', '[', ']', '{', '}', '<', '>',
                        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])

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
