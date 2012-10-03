#! /usr/bin/python

import glob
import argparse
import os.path
import xml.dom.minidom
import subprocess
import getpass

import __init__

from SDS.utils.various import get_text_from_xml_node

if __name__ == '__main__':

  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
      This program copies the collected feedbacks using SCP to the specified destination.
      It is possible that it has to be run under sudo, since the Apache server created 
      the log directories under www-data user and no-one else can write in these directories.
      We need write access to mark which directories where already copied.

      It scans 'feedback.xml' to extract the target location of the feedback.
    """)

  parser.add_argument('indir', action="store", default = './',
                      help='an input directory with feedback.xml files (default value "./")')
  parser.add_argument('user', action="store", 
                      help='the target user name')
  parser.add_argument('server', action="store", 
                      help='the target server')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose oputput')
  parser.add_argument('-f', action="store_true", default=False, dest="force",
                      help='force copy, copy feedback.xml file even if it was coppued before')

  args = parser.parse_args()

  indir = args.indir
  verbose = args.verbose
  user = args.user
  server = args.server
  force = args.force

  password = getpass.getpass("Enter the target server password: ")

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
      
    copy_feedback = force or not os.path.exists(f+".copied")

    if copy_feedback:
      doc = xml.dom.minidom.parse(f)
      els = doc.getElementsByTagName("dialogueId")

      if els:
        target = get_text_from_xml_node(els[0])
        
        if verbose:
          print "Target: ", target
        
        cmd = "pscp -p -pw %s %s %s@%s:%s" % (password,f,user,server,target)

        subprocess.call(cmd, shell=True)
        
        fc = open(f+".copied", "w")
        fc.write("copied\n")
        fc.close()
    else:
      if verbose:
        print "The feedback was already copied:"

