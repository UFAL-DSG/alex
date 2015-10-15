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
import random
import subprocess
import shutil

from alex.utils.fs import find

def mdine(path):
    "Maked dirs if not exist"
    if not os.path.exists(path):
        os.makedirs(path)

def to_wav(src_path, wav_path, encoding = 'gsm'):
    cmd = 'sox --ignore-length {src_path} -r 8000 -t {encoding} - | sox -t {encoding} - -r 16000 -b 16 -e signed-integer {wav_path}'.format(src_path=src_path, wav_path=wav_path, encoding=encoding)
    print cmd
    print

    subprocess.call(cmd, shell=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Convert wave files into gsm and amr-nb formats and back to wav.

      """)

    parser.add_argument('-i', '--input',
                        action="store",
                        help='an input directory with all wav files')
    parser.add_argument('-o', '--output',
                        action="store",
                        help='an output directory for the converted wav')
    parser.add_argument('-v',
                        action="store_true",
                        dest="verbose",
                        help='set verbose output')
    
    args = parser.parse_args()

    
    trn_files = find(args.input, '*.trn', mindepth=1, maxdepth=5)
    
    for fn in trn_files:
        if args.verbose:
            print "Processing file:", fn
            
        real_fn = os.path.realpath(fn)
        base_fn = os.path.basename(fn)

        wav_fn = real_fn.replace('.trn', '')
        trn_fn = real_fn

        if not os.path.exists(wav_fn) or not os.path.exists(wav_fn+'.trn'):
            print "Does not exists {fn} or {fnt}".format(fn=wav_fn, fnt=wav_fn+'.trn')
            continue

        if os.path.getsize(wav_fn) < 5000:
            print "Too small wave file {fn}".format(fn=wav_fn)
            continue

        sub = "{r:02}".format(r=random.randint(0, 99)), "{r:02}".format(r=random.randint(0, 99))
        
        for enc in ['gsm', 'amr-nb']:
            tgt_wav_base_fn = base_fn.replace('.trn', '')
            tgt_wav_base_fn ='{tgt_wav_base_fn}.{enc}.wav'.format(tgt_wav_base_fn=tgt_wav_base_fn, enc=enc)
            
            tgt_wav = os.path.join(args.output, sub[0], sub[1], tgt_wav_base_fn)
            tgt_trn = tgt_wav+'.trn'

            mdine(os.path.join(args.output, sub[0], sub[1]))
            
            to_wav(wav_fn, tgt_wav, enc)
            shutil.copy(trn_fn, tgt_trn)
            
