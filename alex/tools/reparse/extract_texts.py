#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

"""
Extract textual utterances and corresponding SLU interpretaions
from call logs with transcriptions.

Usage:

    ./extract-texts.py path/to/base-log-directory > out-file.txt


Outputs a file in the following format:

    > USER/SYSTEM : <tab> dialogue act <tab> utterance


Different dialogues are separated by two blank lines.
"""

import codecs
import sys
import xml.dom.minidom
import os
import re
import argparse

_TRANSC_NAME_ = 'asr_transcribed.xml'
_LOG_NAME_ = 'session.xml'

stdout = codecs.getwriter('UTF-8')(sys.stdout)

def get_text(xml_elem, tag_name, concat=True):
    """Extract text from a XML element, strip whitespace."""

    sub_elems = xml_elem.getElementsByTagName(tag_name)
    if not sub_elems:
        return None
    if not concat:
        sub_elems = [sub_elems[0]]
    text =  ' '.join([tn.data
                      for sub_elem in sub_elems
                      for tn in sub_elem.childNodes])
    text = re.sub('[\n\t]', ' ', text)
    text = re.sub(' +', ' ', text)
    text = text.strip()
    return text


def process_call(calldir):
    """Process one dialogue."""

    if not os.path.isfile(os.path.join(calldir, _TRANSC_NAME_)):
        print >> sys.stderr, '!No transcription file found for:', calldir

    with open(os.path.join(calldir, _TRANSC_NAME_), 'r') as f:
        try:
            data = xml.dom.minidom.parse(f)
        except:
            print >> sys.stderr, '!Cannot parse:', f
            return

        for turn in data.getElementsByTagName('turn'):

            print >> stdout, ">", turn.getAttribute('speaker').upper(), ":\t",
            if turn.getAttribute('speaker') == 'system':
                print >> stdout, get_text(turn, 'dialogue_act'), "\t", get_text(turn, 'text')

            elif turn.getAttribute('speaker') == 'user':
                slu = turn.getElementsByTagName('slu')
                slu_text = get_text(slu[0], 'interpretation', False) if slu else '???'
                transc_text = get_text(turn, 'asr_transcription')
                if transc_text is None:
                    print >> sys.stderr, '!Empty transcription in ', f
                print >> stdout, slu_text, "\t", transc_text

        print >> stdout, "\n"


def main(logs_path):
    """Process all the directories and print the output."""

    session_dirs = [d for d, _, fs in os.walk(logs_path) if _LOG_NAME_ in fs]

    for session_dir in session_dirs:
        print >> sys.stderr, 'Processing', session_dir
        process_call(session_dir)


if __name__ == '__main__':

    ap = argparse.ArgumentParser()
    ap.add_argument('logdir', help='base path where to search for logs')

    args = ap.parse_args()
    main(args.logdir)

