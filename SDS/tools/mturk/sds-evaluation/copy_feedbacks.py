#! /usr/bin/python

import glob
import argparse

if __name__ == '__main__':
  random.seed(1)

  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
      This program copies the collected feedbacks using SCP to the right place.

      It scans 'feedback.xml' to extract the target location of the feedback.

    """)

  parser.add_argument('indir', action="store",
                      help='an input directory with feedback.xml files')
  parser.add_argument('server', action="store",
                      help='the target server')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose oputput')

  args = parser.parse_args()

  indir = args.indir
  verbose = args.verbose
  server = args.server

  # get all feedbacks
  files = []
  files.append(glob.glob(os.path.join(indir, 'feedback.xml')))
  files.append(glob.glob(os.path.join(indir, '*', 'feedback.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', 'feedback.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', 'feedback.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', 'feedback.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', '*', 'feedback.xml')))

  for f in files:

      if verbose:
        print f
