#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Splits a wave files in a data driectory into train, dev, test directories according to a list of dev and test wave files.
"""
# Make sure the alex package is visible.
if __name__ == '__main__':
    import autopath

import argparse
import os
import os.path
import sys


from alex.utils.fs import find

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Splits a wave files in a data driectory into train, dev, test directories according to a list of dev and test wave files.

      """)

    parser.add_argument('--all',
                        action="store",
                        help='an input directory with all wav files')
    parser.add_argument('--train',
                        action="store",
                        help='an output train directory for files with audio and their transcription')
    parser.add_argument('--dev',
                        action="store",
                        help='an output dev directory for files with audio and their transcription')
    parser.add_argument('--test',
                        action="store",
                        help='an output test directory for files with audio and their transcription')
    parser.add_argument('--devlist',
                        action="store",
                        help='a list of dev wav files')
    parser.add_argument('--testlist',
                        action="store",
                        help='a list of test wav files')
    parser.add_argument('-v',
                        action="store_true",
                        dest="verbose",
                        help='set verbose output')
    
    args = parser.parse_args()

    
    with open(args.devlist, 'r') as f:
        dev_files = set([os.path.basename(fn.strip()) for fn in f.readlines()])
    with open(args.testlist, 'r') as f:
        test_files = set([os.path.basename(fn.strip()) for fn in f.readlines()])
        
    
    all_files = find(args.all, '*.wav', mindepth=1, maxdepth=5)
    
    for fn in all_files:
        if args.verbose:
            print "Processing file:", fn
            
        base_fn = os.path.basename(fn)
        
        if base_fn in dev_files:
            os.system("ln -s {src} {tgt}".format(src = os.path.join('..', args.all, base_fn), tgt = os.path.join(args.dev, base_fn)))
            os.system("ln -s {src} {tgt}".format(src = os.path.join('..', args.all, base_fn+'.trn'), tgt = os.path.join(args.dev, base_fn+'.trn')))
        elif base_fn in test_files:
            os.system("ln -s {src} {tgt}".format(src = os.path.join('..', args.all, base_fn), tgt = os.path.join(args.test, base_fn)))
            os.system("ln -s {src} {tgt}".format(src = os.path.join('..', args.all, base_fn+'.trn'), tgt = os.path.join(args.test, base_fn+'.trn')))
        else:
            os.system("ln -s {src} {tgt}".format(src = os.path.join('..', args.all, base_fn), tgt = os.path.join(args.train, base_fn)))
            os.system("ln -s {src} {tgt}".format(src = os.path.join('..', args.all, base_fn+'.trn'), tgt = os.path.join(args.train, base_fn+'.trn')))
