#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys

import __init__

import SDS.utils.audio as audio
import SDS.utils.various as various

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.vad import VAD
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
    'allowed_phone_numbers': r"(^[234567])",
    'forbidden_match_phone_number': r"(^112$|^150$|^155$|^156$|^158$)",

    'domain': 'your_domain',
    'user': 'your_user',
    'password': 'your_password',
  },
  'VAD': {
    'debug': False,
    'type': 'power',
    'power_threshold': 300,
    'power_threshold_multiplier': 1,
    'power_adaptation_frames': 20,
    'power_decision_frames': 25,
    'power_decision_speech_threshold': 0.7,
    'power_decision_non_speech_threshold': 0.2,
  },
  'Hub': {
    'main_loop_sleep_time': 0.005,
  },
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the VoipIO and VAD components:"
print "="*120

wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
# split audio into frames
wav = various.split_to_bins(wav, 2*cfg['Audio']['samples_per_frame'])
# remove the last frame

vio_commands, vio_child_commands = multiprocessing.Pipe() # used to send vio_commands
audio_record, child_audio_record = multiprocessing.Pipe() # I read from this connection recorded audio
audio_play, child_audio_play = multiprocessing.Pipe()     # I write in audio to be played
audio_played, child_audio_played = multiprocessing.Pipe() # I read from this to get played audio
                                                          #   which in sync with recorded signal

vad_commands, vad_child_commands = multiprocessing.Pipe() # used to send commands to VAD
vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

vio = VoipIO(cfg, vio_child_commands, child_audio_record, child_audio_play, child_audio_played)
vad = VAD(cfg, vad_child_commands, audio_record, audio_played, vad_child_audio_out)

command_connections = [vio_commands, vad_commands]

vio.start()
vad.start()

count = 0
max_count = 50000
while count < max_count:
  time.sleep(cfg['Hub']['main_loop_sleep_time'])
  count += 1

  # write one frame into the audio output
  if wav:
    data_play = wav.pop(0)
    #print len(wav), len(data_play)
    audio_play.send(Frame(data_play))

  # read all VAD output audio
  if vad_audio_out.poll():
    data_vad = vad_audio_out.recv()

    if isinstance(data_vad, Command):
      if data_vad.parsed['__name__'] == 'speech_start':
        print 'VAD:', 'Speech start'
      if data_vad.parsed['__name__'] == 'speech_end':
        print 'VAD:', 'Speech end'

  # read all messages
  for c in command_connections:
    if c.poll():
      command = c.recv()
      print
      print command
      print

  sys.stdout.flush()

vio_commands.send(Command('stop()'))
vad_commands.send(Command('stop()'))
vio.join()
vad.join()

print
