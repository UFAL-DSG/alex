#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import glob
import os.path
import argparse
import subprocess

import __init__

from SDS.utils.various import flatten, get_text_from_xml_node

def create_mlf(indir, outfile, verbose):
    # get all transcriptions
    files = []
    files.append(glob.glob(os.path.join(indir, '*.wav')))
    files.append(glob.glob(os.path.join(indir, '*', '*.wav')))
    files.append(glob.glob(os.path.join(indir, '*', '*', '*.wav')))
    files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*.wav')))
    files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', '*.wav')))
    files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', '*', '*.wav')))

    files = flatten(files)

    mlf = open(outfile, "w")
    mlf.write("#!MLF!#\n")
    size = 0
    for f in files:

        if verbose:
            print "Processing wav file: ", f

        wav_stats = subprocess.check_output("soxi %s" % f, shell=True)
        wav_stats = wav_stats.split('\n')

        mfc = f.replace('.wav', ".mfc")
        subprocess.check_output("HCopy -T 1 -C config -C configwav %s %s" % (f, mfc), shell=True)

        for l in wav_stats:
            if l.startswith('Duration'):
                l = l.split()
                time = [float(x) for x in l[2].split(':')]
                time = time[0]*60*60 + time[1]*60 + time[2]

                # convert time into HTK 100ns units
                time = int(time*10000000)

                size += time

        f = f.replace(".wav", ".lab").replace("data/", "*/")
        mlf.write('"%s"\n' % f)
        mlf.write('0 %d sil\n' % time)
        mlf.write(".\n")

    mlf.close()

    hour = size / 10000000 / 3600.0

    print "Length of audio data in hours:", hour

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
      description="""
        This program create a MLF file which labels all data as silence (sil).
      """)

    parser.add_argument('indir', action="store",
                        help='an input directory with wav files')
    parser.add_argument('outfile', action="store",
                        help='an output MLF files with audio audio labeled as silence')
    parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                        help='set verbose oputput')

    args = parser.parse_args()

    create_mlf(args.indir, args.outfile, args.verbose)
