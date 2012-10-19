#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import codecs

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
      description="""
        Processes Julius ASR raw output and generates an MLF file with results of decoding.

      """)

    parser.add_argument('--log', action="store", help='input Julius ASR log file')
    parser.add_argument('--mlf', action="store", help='output MLF file')

    args = parser.parse_args()

    flog = codecs.open(args.log, 'r', 'utf-8')
    fmlf = codecs.open(args.mlf, 'w', 'utf-8')

    fmlf.write("#!MLF!#\n")

    for l in flog:
        l = l.strip()
        if "input MFCC file: " in l:
            ri = l.rindex("/")
            l = l[ri:]
            l = l.replace('.wav','.rec')
            fmlf.write('"*%s"\n' % l)
        if "input speechfile: " in l:
            ri = l.rindex("/")
            l = l[ri:]
            l = l.replace('.wav','.rec')
            fmlf.write('"*%s"\n' % l)

        if "sentence1: " in l:
            ri = l.rindex("sentence1: ")
            l = l[ri+len("sentence1: "):]
            l = l.split()
            fmlf.write('\n'.join(l))
            fmlf.write('\n.\n')

    flog.close()
    fmlf.close()
