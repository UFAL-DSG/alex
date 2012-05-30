#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os.path
import argparse
import xml.dom.minidom
import shutil

import __init__

from SDS.utils.various import flatten, get_text_from_xml_node

"""
This program process CUED call log files and copies all audio into a destination directory.
It also extracts transcriptions from the log files and saves them alongside the copied wavs.

It scans for 'user-transcription.norm.xml' to extract transcriptions and names of wave files.

"""

def save_transcription(transcription_file_name, transcription):
  f = open(transcription_file_name, 'w+')
  f.write(transcription)
  f.close()

def extract_wavs_trns(file, outdir, waves_mapping, verbose):
  """Extracts wavs and their transcriptions from the provided CUED call log file."""

  # load the file
  doc = xml.dom.minidom.parse(file)
  els = doc.getElementsByTagName("userturn")

  size = 0
  for el in els:
    transcription = el.getElementsByTagName("transcription")
    audio = el.getElementsByTagName("rec")

    if len(transcription) != 1 or len(audio) != 1:
      # skip this node, it contains multiple elements of either transcription or audio.
      continue

    audio = audio[0].getAttribute('fname').strip()
    transcription  = get_text_from_xml_node(transcription[0])

    if verbose:
      print " # f:", audio, "t:", transcription

    dir = os.path.dirname(file)

    audio_file_name = waves_mapping[audio]
    transcription_file_name = os.path.join(outdir, audio + '.trn')

    try:
      size += os.path.getsize(audio_file_name)
      shutil.copy2(audio_file_name, outdir)
      save_transcription(transcription_file_name, transcription)
    except OSError:
      print "Missing audio file:", audio_file_name

  return size

def get_waves_mapping(indir_audio):
  mapping = {}

  files = []
  files.append(glob.glob(os.path.join(indir_audio, '*', '*.wav')))
  files.append(glob.glob(os.path.join(indir_audio, '*', '*', '*.wav')))
  files.append(glob.glob(os.path.join(indir_audio, '*', '*', '*', '*.wav')))
  files.append(glob.glob(os.path.join(indir_audio, '*', '*', '*', '*', '*.wav')))
  files.append(glob.glob(os.path.join(indir_audio, '*', '*', '*', '*', '*', '*.wav')))

  files = flatten(files)

  for f in files:
    mapping[os.path.basename(f)] = f

  return mapping

def convert(indir, indir_audio, outdir, verbose):
  # get all wave files
  waves_mapping = get_waves_mapping(indir_audio)

  # get all transcriptions
  files = []
  files.append(glob.glob(os.path.join(indir, '*', 'user-transcription.norm.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', 'user-transcription.norm.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', 'user-transcription.norm.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', 'user-transcription.norm.xml')))
  files.append(glob.glob(os.path.join(indir, '*', '*', '*', '*', '*', 'user-transcription.norm.xml')))

  files = flatten(files)

  size = 0
  for f in files:

    if verbose:
      print "Processing call log file: ", f

      size += extract_wavs_trns(f, outdir, waves_mapping, verbose)


  print "Size of copied audio data:", size

  sec  = size / 16000*2
  hour = sec / 3600.0

  print "Length of audio data in hours:", hour

if __name__ == '__main__':
  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""
    This program process CUED call log files and copies all audio into a destination directory.
    It also extracts transcriptions from the log files and saves them alongside the copied wavs.

    It scans for 'user-transcription.norm.xml' to extract transcriptions and names of wave files.

    """)

  parser.add_argument('indir', action="store",
                      help='an input directory with CUED call log files')
  parser.add_argument('indir_audio', action="store",
                      help='an input directory with CUED audio files')
  parser.add_argument('outdir', action="store",
                      help='an output directory for files with audio and their transcription')
  parser.add_argument('-v', action="store_true", default=False, dest="verbose",
                      help='set verbose oputput')

  args = parser.parse_args()

  convert(args.indir, args.indir_audio, args.outdir, args.verbose)
