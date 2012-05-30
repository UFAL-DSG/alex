#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os.path
import re
import argparse

import __init__

from SDS.corpustools.cuedda import CUEDDialogueAct

"""
This program processes the CUED call logs for <semitran> tags, converts the CUED semantic annotations
therein to the UFAL semantic format and stores them in a <semitran_ufal> tag.

It scans for all */*/user-transcription.norm.xml files in the directory given by the --indir argument.
By default, this is ./cued_call_logs.

The files are processed in-place.

"""

def process_log(infile,outfile,verbose):

  # We only need to find the <semitrans> line in each user turn in the file and
  # append a <semitran_ufal> line with the converted dialogue state.
  f = open(infile,'r')
  g = open(outfile,'w')
  for line in f:
    isSemitran = re.search(r'([^<]*)<semitran>(.*)</semitran>',line)

    if isSemitran:
      whitespace_at_start_of_line = isSemitran.group(1)
      cued_da = isSemitran.group(2)
      da = CUEDDialogueAct("",cued_da) # Doesn't need any text.
      da.parse()

      ufal_da = da.get_ufal_da()
      g.write(line)
      g.write(whitespace_at_start_of_line + "<semitran_ufal>" + ufal_da + "</semitran_ufal>\n")
    else:
      g.write(line)

  f.close()
  g.close()


###############################################

if __name__ == '__main__':
  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
    This program processes the CUED call logs for <semitran> tags, converts the UCED semantic annotations
    therein to the UFAL semantic format and stores them in a <semitran_ufal> tag.

    It scans for all */user-transcription.norm.xml files in the directory given by the --indir argument.
    By default, this is ./cued_call_logs.

    The resulting files (with both <semitrans> and <semitrans_ufal>) are named ufalized-user-transcription.norm.xml.
    The prefix can also be specified by the --prefix arguement.

    The --outdir argument controls the destination folder of ufalized files. If given, all the output files
    will be written to that directory, without preserving the original directory structure. If not given,
    the output files go to the directories where they came from.

    """)

  parser.add_argument('--indir', action="store", default='./cued_call_logs',
                      help='an input directory with CUED call log */*/*.xml files (default: ./cued_call_logs)')
  parser.add_argument('--prefix', action="store", default='ufalized',
                      help='a prefix for the modified files.')
  parser.add_argument('--outdir', action="store", default='NONE',
                      help='optional output directory where all the modified files will be written (without dir. structure)')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose output')

  args = parser.parse_args()

  indir = args.indir
  prefix = args.prefix
  outdir = args.outdir
  verbose = args.verbose

  # Searching for all call logs:
  logs = glob.glob(os.path.join(indir, '*', '*', 'user-transcription.norm.xml'))
  logs.sort()

  index = 0
  for log in logs:

    # Generate outfile name
    outfile = log
    if 'NONE' in outdir:
      bnfn = os.path.basename(log)
      outfile = os.path.join(os.path.dirname(log), prefix + '-' + bnfn)
    else:
      bnfn = os.path.basename(log)
      pathmatch = re.search(r'([^/]*$)',os.path.dirname(log))
      midpath = ""
      if pathmatch:
        midpath = pathmatch.group(1)
      outfile = os.path.join(outdir, prefix + '-' + midpath + '-' + bnfn)

    if verbose:
      print 'Processing: ', log
      print 'Output to: ', outfile

    process_log(log,outfile,verbose)
