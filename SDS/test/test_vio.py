#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import sys
import time

import __init__

import SDS.utils.audio as audio
import SDS.utils.various as various

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.messages import Command, Frame

cfg = {
  'Audio': {
    'sample_rate': 8000,
    'samples_per_frame': 128,
  },
  'VoipIO': {
    'pjsip_log_level': 3,
    'debug': True,
    'reject_calls': False,
    'call_back': False,
    'allowed_phone_numbers': r"(^[234567])",
    'forbidden_match_phone_number': r"(^112$|^150$|^155$|^156$|^158$)",

    'domain': 'your_domain',
    'user': 'your_user',
    'password': 'your_password',
  },
  'Hub': {
    'main_loop_sleep_time': 0.005,
  },
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the VoipIO component:"
print "="*120

wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
# split audio into frames
wav = various.split_to_bins(wav, 2*cfg['Audio']['samples_per_frame'])
# remove the last frame

vio_commands, vio_child_commands = multiprocessing.Pipe() # used to send vio_commands
vio_messages, vio_child_messages = multiprocessing.Pipe() # used to send vio_messages
audio_record, child_audio_record = multiprocessing.Pipe() # I read from this connection recorded audio
audio_play, child_audio_play     = multiprocessing.Pipe() # I write in audio to be played
audio_played, child_audio_played = multiprocessing.Pipe() # I read from this to get played audio
                                                          #   which in sync with recorded signal

vio = VoipIO(cfg, vio_child_commands, child_audio_record, child_audio_play, child_audio_played)

vio.start()

count = 0
max_count = 25000
while count < max_count:
  time.sleep(cfg['Hub']['main_loop_sleep_time'])
  count += 1

  # write one frame into the audio output
  if wav:
    data_play = wav.pop(0)
    #print len(wav), len(data_play)
    audio_play.send(Frame(data_play))

  # read all recorded audio
  if audio_record.poll():
    data_rec = audio_record.recv()
  # read all played audio
  if audio_played.poll():
    data_played = audio_played.recv()

  # read all messages from VoipIO
  if vio_commands.poll():
    command = vio_commands.recv()
    if isinstance(command, Command):
      print
      print command
      print

  sys.stdout.flush()

vio_commands.send(Command('stop()'))
vio.join()

print
