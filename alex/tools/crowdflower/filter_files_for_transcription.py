#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage: ./filter_files_for_transcription.py <dir> > filelist.lst 2> log.txt

Create a list of audio files for transcription, filtering "obvious" 
texts so that wont't transcribe things that the ASR is good at.

The obvious texts are preset to "thank you goodbye", "yes" and "no"
at the probability of > 0.9 (you may change this in the code).
"""

from __future__ import unicode_literals
import codecs
import sys
import os.path
import os
import xml.dom.minidom

logfile_name = 'session.xml'

obvious_texts = ['thank you goodbye', 'yes', 'no']
obvious_prob = 0.9

def process_dir(dirname):

    with open(os.path.join(dirname, logfile_name), 'r') as fh:
        try:
            data = xml.dom.minidom.parse(fh)
            header = data.getElementsByTagName('header')[0]
        except:
            print >> sys.stderr, 'CANNOT PARSE LOG:', data
            return

    for rec in data.getElementsByTagName('rec'):
        recfile = os.path.join(dirname, rec.getAttribute('fname'))
        turn = rec.parentNode
        asr = turn.getElementsByTagName('asr')
        if not asr:
            continue
        asr = asr[0]
        hypos = asr.getElementsByTagName('hypothesis')
        if not hypos or not hypos[0].childNodes:  # ASR with no hypotheses: output
            print >> sys.stderr, 'No hypotheses in %s' % recfile
            print os.path.join(dirname, recfile)
            continue
        text = hypos[0].childNodes[0].data
        conf = float(hypos[0].getAttribute('p'))
        if conf > obvious_prob and text.lower() in obvious_texts:
            print >> sys.stderr, 'Skipping %s with p=%4.3f in %s' % (text, conf, recfile)
            continue
        print >> sys.stderr, 'ASR needed for %s with p=%4.3f in %s' % (text, conf, recfile)
        print os.path.join(dirname, recfile)


def main(base_path='.'):
    dirs = [d for d in os.listdir(base_path) if os.path.isdir(d) 
            and os.path.isfile(os.path.join(d, logfile_name))]

    for dirname in dirs:
        process_dir(dirname)


if __name__ == '__main__':
    main(sys.argv[1])
