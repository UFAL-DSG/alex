#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

import re
import argparse
import sys

from alex.corpustools.wavaskey import load_wavaskey
from alex.components.asr.utterance import Utterance
from alex.utils.text import min_edit_dist, min_edit_ops

def score_file(reftext, testtext):
    """
    Computes ASR scores between reference and test word strings.

    :param reftext:
    :param testtext:
    :return: a tuple with percentages of correct, substitutions, deletions, insertions, error rate, and a number of reference words.
    """
    ii, dd, ss, nn = 0.0, 0.0, 0.0, 0.0

    for utt_idx in sorted(reftext):
        r = re.sub(ur"\b_\w+_\b",r"",unicode(reftext[utt_idx]).lower(),flags=re.UNICODE).split()
        t = re.sub(ur"\b_\w+_\b",r"",unicode(testtext[utt_idx]).lower(),flags=re.UNICODE).split()
#        r = unicode(reftext[utt_idx]).lower().split()
#        t = unicode(testtext[utt_idx]).lower().split()
        i, d, s = min_edit_ops(t, r)

        ii += i
        dd += d
        ss += s

        nn += len(r)

#        print "Ref:", unicode(r)
#        print "Tst:", unicode(t)
#        print i, d, s, len(r)
#        print ii, dd, ss, nn
#        print

    return (nn-ss-dd)/nn*100, ss/nn*100, dd/nn*100, ii/nn*100, (ss+dd+ii)/nn*100, nn

def score(fn_reftext, fn_testtext, outfile = sys.stdout):
    reftext  = load_wavaskey(fn_reftext, Utterance)
    testtext = load_wavaskey(fn_testtext, Utterance)

    corr, sub, dels, ins, wer, nwords = score_file(reftext, testtext)

    m ="""
    Please note that the scoring is implicitly ignoring all non-speech events.
    
    Ref: {r}
    Tst: {t}
    |==============================================================================================|
    |            | # Sentences  |  # Words  |   Corr   |   Sub    |   Del    |   Ins    |   Err    |
    |----------------------------------------------------------------------------------------------|
    | Sum/Avg    |{num_sents:^14}|{num_words:^11.0f}|{corr:^10.2f}|{sub:^10.2f}|{dels:^10.2f}|{ins:^10.2f}|{wer:^10.2f}|
    |==============================================================================================|
    """.format(r=fn_reftext, t=fn_testtext, num_sents = len(reftext), num_words = nwords, corr=corr, sub = sub, dels = dels, ins = ins, wer = wer)

    outfile.write(m)
    outfile.write("\n")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="""
    Compute ASR scores for ASR output against reference text.
    The scoring implicitly ignores non-speech events in comparison.

    The files structures must be as follows:
      text_name    => text_content
      ----------------------------------------
      0000001.wav => I want Chinese food
      0000002.wav => Give me the phone number

    The text from the test file and the reference file is matched based on the text_name.
    """)

    parser.add_argument('refsem', action="store", help='a file with reference semantics')
    parser.add_argument('testsem', action="store", help='a file with tested semantics')

    args = parser.parse_args()

    score(args.refsem, args.testsem)
                                        
