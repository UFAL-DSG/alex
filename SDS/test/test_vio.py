#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import sys
import time

import SDS.utils.audio as audio
import SDS.utils.various as various
from SDS.components.hub.vio import VoipIO

# FIX: samples_per_frame should be renamed to samples_per_frame

cfg = {
  'Audio': {
    'sample_rate': 8000
  },
  'VoipIO': {
    'pjsip_log_level': 3,
    'debug': True,
    'vad': True,
    'samples_per_frame': 128,
    'play_buffer_size': 70,

    'domain': 'your_domain',
    'user': 'your_user',
    'password': 'your_password',
  },
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the VoipIO component:"
print "="*120

wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
# split audio into frames
wav = various.split_to_bins(wav, 2*cfg['VoipIO']['samples_per_frame'])
# remove the last frame

vio_commands, vio_child_commands = multiprocessing.Pipe() # used to send vio_commands
audio_record, child_audio_record = multiprocessing.Pipe() # I read from this connection recorded audio
audio_play, child_audio_play     = multiprocessing.Pipe() # I write in audio to be played
audio_played, child_audio_played = multiprocessing.Pipe() # I read from this to get played audio
                                                          #   which in sync with recorded signal

vio = VoipIO(cfg, vio_child_commands, child_audio_record, child_audio_play, child_audio_played)

vio.start()

count = 0
max_count = 25000
while count < max_count:
  time.sleep(0.002)
  count += 1

  # write one frame into the audio output
  if wav:
    data_play = wav.pop(0)
    #print len(wav), len(data_play)
    audio_play.send(data_play)

  # read all recorded audio
  while audio_record.poll():
    data_rec = audio_record.recv()
  # read all played audio
  while audio_played.poll():
    data_played = audio_played.recv()

vio_commands.send('stop()')
vio.join()

print

