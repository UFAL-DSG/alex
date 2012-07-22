#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import glob
import os.path
import argparse
import xml.dom.minidom
import shutil
import random
import collections
import codecs

import __init__

from SDS.utils.various import flatten, get_text_from_xml_node

"""
This program process transcribed audio in Transcriber files and copies all relevant speech segments into a destination directory.
It also extracts transcriptions and saves them alongside the copied wavs.

It scans for '*.trs' to extract transcriptions and names of wave files.

"""

subst = [('JESLTI', 'JESTLI'),
         ('<INHALE>', ''), 
        ]
        
hesitation = [ "UMMM"]

def normalization(text):
  t = text.strip().upper()
  
  t = t.strip().replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
  for a, b in [('.',' '),('?',' '),('!',' '),('"',' '),(',',' '),('_',' '),('^',' '),('*',' ')]:
    t = t.replace(a,b)
         
  t = t.strip().replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
  for p, s in subst:
    t = re.sub('^'+p+' ', s+' ', t)
    t = re.sub(' '+p+' ', ' '+s+' ', t)
    t = re.sub(' '+p+'$', ' '+s, t)
    t = re.sub('^'+p+'$', s, t)
    
  t = t.strip().replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
  for p in hesitation:
    t = re.sub('^'+p+' ', '(HESITATION) ', t)
    t = re.sub(' '+p+' ', ' (HESITATION) ', t)
    t = re.sub(' '+p+'$', ' (HESITATION)', t)
    t = re.sub('^'+p+'$', '(HESITATION)', t)

  t = t.strip().replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')

  return t

def exclude(text):
  for c in ['-', '+', '(', ')', '[', ']', '{', '}',  '<', '>' ]:
    if c in text:
      return True
  
  if len(text) < 2:
    return True 
  
  return False
  

d = collections.defaultdict(int)
def update_dict(text):
  t = text.split()
  
  for w in t:
    d[w] += 1 

def unique_str():
  return hex(random.randint(0, 256*256*256*256-1))[2:]
  
def save_transcription(transcription_file_name, transcription):
  f = codecs.open(transcription_file_name, 'w+', "utf-8")
  f.write(transcription)
  f.close()
  
def extract_wavs_trns(file, outdir, verbose):
  """Extracts wavs and their transcriptions from the provided big wav and the transcriber file."""
  
  # load the file
  doc = xml.dom.minidom.parse(file)
  els = doc.getElementsByTagName("Sync")

  size = 0
  for el in els:
    print '-'*120
    
    time = float(el.getAttribute('time').strip())
    if el.nextSibling.nodeType == el.TEXT_NODE:
      transcription = el.nextSibling.data.strip()
    else :
      transcription = ''
      
    s_audio_file_name = file.replace('.trs', '.wav')
    t_ext = '-%06.2f-%s.wav' % (time, unique_str())
    t_audio_file_name = os.path.join(outdir, os.path.basename(file).replace('.trs', t_ext))
    transcription_file_name = t_audio_file_name + '.trn'

    if verbose:
      print " # f:", os.path.basename(t_audio_file_name)," # t:", time, "t:", transcription

    transcription = normalization(transcription)
    if verbose:
      print " # f:", os.path.basename(t_audio_file_name)," # t:", time, "t:", transcription
      
    if exclude(transcription): 
      continue
    
    update_dict(transcription)
    if verbose:
      print " # f:", os.path.basename(t_audio_file_name)," # t:", time, "t:", transcription


    try:
#      size += os.path.getsize(audio_file_name)
      save_transcription(transcription_file_name, transcription)
    except OSError:
      print "Missing audio file:", audio_file_name
    
  return size
  
def convert(indir, outdir, verbose):
  # get all transcriptions
  files = []
  files.append(glob.glob(os.path.join(indir, '*.trs')))
  files.append(glob.glob(os.path.join(indir, '*', '*.trs')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*.trs')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*.trs')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', '*.trs')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', '*', '*.trs')))
  
  files = flatten(files)
  
  size = 0
  for f in files:

    if verbose:
      print "Processing call log file: ", f

      size += extract_wavs_trns(f, outdir, verbose)


  print "Size of copied audio data:", size

  sec  = size / 16000*2
  hour = sec / 3600.0

  print "Length of audio data in hours (for 8kHz 16b WAVs):", hour
  
if __name__ == '__main__':
  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
      This program process transcribed audio in Transcriber (*.trs) files and copies all relevant speech segments into a destination directory.
      It also extracts transcriptions and saves them alongside the copied wavs.

      It scans for '*.trs' to extract transcriptions and names of wave files.
      
    """)

  parser.add_argument('indir', action="store",
                      help='an input directory with trs and wav files')
  parser.add_argument('outdir', action="store",
                      help='an output directory for files with audio and their transcription')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose oputput')

  args = parser.parse_args()

  convert(args.indir, args.outdir, args.verbose)

  f = codecs.open('word_list', 'w', "utf-8")
  for w in sorted(d.keys()):
    f.write("%s\t%d" % (w, d[w]))
    f.write('\n')
  f.close()
  
