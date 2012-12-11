#!/usr/bin/python
# -*- coding: UTF-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
Reads names of call log dirs from a list and copies related recordings plus
their transcriptions, extracted from a corresponding XML file, to a specified
destination directory.

2012-12-11
Matěj Korvas
"""

import argparse
import os.path
import shutil
from xml.etree import ElementTree


if __name__ == '__main__':
    # Parse arguments.
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="""
        Extracts transcriptions from XML files ('user-transcription.xml' by
        default)

      """)

    parser.add_argument('log_dirs_list', action="store",
                        help='path towards a file listing call log dirs')
    parser.add_argument('outdir', action="store",
                        help='path towards the output directory for copying '
                             'the wavs and their transcriptions')
    parser.add_argument('-x', '--xml-name',
                        action="store",
                        default="user-transcription.xml",
                        help='name of XML files containing the transcriptions')
    parser.add_argument('-t', '--trn-ext',
                        action="store",
                        default="trn",
                        help='the filename extension for transcriptions')
    parser.add_argument('-v', '--verbose',
                        action="store_true",
                        help='be verbose')

    args = parser.parse_args()

    dirnames = list()
    with open(args.log_dirs_list, 'r') as dirlist:
        for line in dirlist:
            dirnames.append(line.strip())
    for dirname in dirnames:
        xml_fname = os.path.join(dirname, args.xml_name)
        try:
            doc = ElementTree.parse(xml_fname)
        except IOError as error:
            print '!!! Could not parse "{fname}": {msg!s}.'\
                  .format(fname=xml_fname, msg=error)
            continue
        uturns = doc.findall(".//userturn")
        for uturn in uturns:
            rec = uturn.find("rec")
            trs = uturn.find("transcription")
            if rec is not None and trs is not None:
                wav_fname = rec.get('fname')
                from_wav = os.path.join(dirname, wav_fname)
                to_wav = os.path.join(args.outdir, wav_fname)
                shutil.copy(from_wav, to_wav)
                trs_fname = to_wav + '.' + args.trn_ext
                with open(trs_fname, 'w') as trs_file:
                    trs_file.write(trs.text + '\n')
                if args.verbose:
                    print '{from_} -> {to}'.format(from_=from_wav, to=to_wav)
                    print 'Created {trs}:'.format(trs=trs_fname)
                    print '  "{text}"'.format(text=trs.text)
