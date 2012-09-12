#! /usr/bin/python

import glob
import argparse
import os.path
import xml.dom.minidom
import subprocess

import __init__

from SDS.utils.various import get_text_from_xml_node

if __name__ == '__main__':

  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
      This program copies the collected feedbacks using SCP to the right place.

      It scans 'feedback.xml' to extract the target location of the feedback.
    """)

  parser.add_argument('indir', action="store", default = './',
                      help='an input directory with feedback.xml files (default value "./")')
  parser.add_argument('server', action="store", 
                      help='the target server')
  parser.add_argument('password', action="store",
                      help='the server password')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose oputput')

  args = parser.parse_args()

  indir = args.indir
  verbose = args.verbose
  server = args.server
  password = args.password

  # get all feedbacks
  files = []
  files.extend(glob.glob(os.path.join(indir, 'feedback.xml')))
  files.extend(glob.glob(os.path.join(indir, '*', 'feedback.xml')))
  files.extend(glob.glob(os.path.join(indir, '*', '*', 'feedback.xml')))
  files.extend(glob.glob(os.path.join(indir, '*', '*', '*', 'feedback.xml')))
  files.extend(glob.glob(os.path.join(indir, '*', '*', '*', '*', 'feedback.xml')))
  files.extend(glob.glob(os.path.join(indir, '*', '*', '*', '*', '*', 'feedback.xml')))

  for f in sorted(files):
    if verbose:
      print "Input feedback:", f
      
      
    doc = xml.dom.minidom.parse(f)
    els = doc.getElementsByTagName("dialogueId")

    if els:
      target = get_text_from_xml_node(els[0])
      
      print "Target: ", target
      
      cmd = "pscp -p -pw %s %s %s:%s" % (password,f,server,target)
      
      subprocess.call(cmd, shell=True)
      
