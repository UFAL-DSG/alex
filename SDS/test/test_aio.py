#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import sys
import time

import SDS.utils.audio as audio
import SDS.utils.various as various
from SDS.components.hub.aio import AudioIO

cfg = {
  'Audio': {
      'sample_rate': 8000
  },
  'AudioIO': {
    'debug': True,
    'vad': True,
    'samples_per_buffer': 80,
    'play_buffer_size': 70,
  },
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the AudioIO component:"
print "="*120

wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
# split audio into frames
wav = various.split_to_bins(wav, 2*cfg['AudioIO']['samples_per_buffer'])
# remove the last frame

aio_commands, aio_child_commands = multiprocessing.Pipe() # used to send aio_commands
audio_record, child_audio_record = multiprocessing.Pipe() # I read from this connection recorded audio
audio_play, child_audio_play     = multiprocessing.Pipe() # I write in audio to be played
audio_played, child_audio_played = multiprocessing.Pipe() # I read from this to get played audio
                                                          #   which in sync with recorded signal

aio = AudioIO(cfg, aio_child_commands, child_audio_record, child_audio_play, child_audio_played)

aio.start()

count = 0
max_count = 2500
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

aio_commands.send('stop()')
aio.join()

print


