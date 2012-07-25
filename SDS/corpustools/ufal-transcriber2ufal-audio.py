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
import subprocess

import __init__

from SDS.utils.various import flatten, get_text_from_xml_node

"""
This program process transcribed audio in Transcriber files and copies all relevant speech segments into a destination directory.
It also extracts transcriptions and saves them alongside the copied wavs.

It scans for '*.trs' to extract transcriptions and names of wave files.

"""

subst = [('<SILENCE>', '_SIL_'),
         ('<INHALE>', '_INHALE_'),
         ('<NOISE>', '_NOISE_'),
         ('<COUGH>', '_EHM_HMM_'),
         ('<MOUTH>', '_EHM_HMM_'),
         ('<LAUGH>', '_LAUGH_'),
         ('<EHM A>', '_EHM_HMM_'),
         ('<EHM N>', '_EHM_HMM_'),
         ('<EHM >', '_EHM_HMM_'),
         ('JESLTI', 'JESTLI'),
         ('NMŮŽU', 'NEMŮŽU'),
         ('6E', ' '),
]

hesitation = [ "UMMM"]

excluded_caracters = ['|', '-', '=', '(', ')', '[', ']', '{', '}',  '<', '>' ]

def normalization(text):
  t = text.strip().upper()

  t = t.strip().replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')
  for a, b in [('.',' '),('?',' '),('!',' '),('"',' '),(',',' '),('_',' '),('^',' ')]:
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
  # remove signs of (1) incorrect pronunciation, (2) stuttering, (3) bargin
  for a, b in [('*',''), ('+',''), ('~',''),]:
    t = t.replace(a,b)

  t = t.strip().replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').replace('  ', ' ')

  return t

def exclude(text):
  for c in excluded_caracters:
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

def cut_wavs(s_audio_file_name, t_audio_file_name, time_s, time_e):
  cmd = "sox %s %s trim %f %f" % (s_audio_file_name, t_audio_file_name, time_s, time_e - time_s)
  print cmd

  subprocess.call(cmd, shell=True)

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

    time_s = float(el.getAttribute('time').strip())
    if el.nextSibling.nodeType == el.TEXT_NODE:
      transcription = el.nextSibling.data.strip()
    else:
      transcription = ''
    try:
      time_e = float(el.nextSibling.nextSibling.getAttribute('time').strip())
    except:
      time_e = 999.000

    s_audio_file_name = file.replace('.trs', '.wav')
    t_ext = '-%06.2f-%06.2f-%s.wav' % (time_s, time_e, unique_str())
    t_audio_file_name = os.path.join(outdir, os.path.basename(file).replace('.trs', t_ext))
    transcription_file_name = t_audio_file_name + '.trn'

    if verbose:
      print " # f:", os.path.basename(t_audio_file_name)," # s:", time_s, "# e:", time_e, "t:", transcription.encode('utf-8')

    transcription = normalization(transcription)
    if verbose:
      print " # f:", os.path.basename(t_audio_file_name)," # s:", time_s, "# e:", time_e, "t:", transcription.encode('utf-8')

    if exclude(transcription):
      continue

    update_dict(transcription)
    if verbose:
      print " # f:", os.path.basename(t_audio_file_name)," # s:", time_s, "# e:", time_e, "t:", transcription.encode('utf-8')


    try:
      cut_wavs(s_audio_file_name, t_audio_file_name, time_s, time_e)
      size += os.path.getsize(t_audio_file_name)
      save_transcription(transcription_file_name, transcription)
    except OSError:
      print "Missing audio file:", t_audio_file_name

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

  sec  = size / 16000
  hour = sec / 3600.0

  print "Length of audio data in hours (for 8kHz 16bit WAVs):", hour

if __name__ == '__main__':
  random.seed(1)

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

