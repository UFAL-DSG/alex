#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time

import __init__

import SDS.utils.audio as audio
import SDS.utils.various as various

from SDS.components.hub.aio import AudioIO
from SDS.components.hub.vad import VAD

cfg = {
  'Audio': {
      'sample_rate': 16000
  },
  'AudioIO': {
    'debug': True,
    'samples_per_frame': 80,
    'play_buffer_size': 70,
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
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the AudioIO and VAD components:"
print "="*120

wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
# split audio into frames
wav = various.split_to_bins(wav, 2*cfg['AudioIO']['samples_per_frame'])
# remove the last frame

aio_commands, aio_child_commands = multiprocessing.Pipe() # used to send commands to AudioIO
audio_record, child_audio_record = multiprocessing.Pipe() # I read from this connection recorded audio
audio_play, child_audio_play = multiprocessing.Pipe()     # I write in audio to be played
audio_played, child_audio_played = multiprocessing.Pipe() # I read from this to get played audio
                                                          #   which in sync with recorded signal

vad_commands, vad_child_commands = multiprocessing.Pipe() # used to send commands to VAD
vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

aio = AudioIO(cfg, aio_child_commands, child_audio_record, child_audio_play, child_audio_played)
vad = VAD(cfg, vad_child_commands, audio_record, audio_played, vad_child_audio_out)

aio.start()
vad.start()

count = 0
max_count = 5000
while count < max_count:
  time.sleep(0.002)
  count += 1

  # write one frame into the audio output
  if wav:
    data_play = wav.pop(0)
    #print len(wav), len(data_play)
    audio_play.send(data_play)

  # read all VAD output audio
  while vad_audio_out.poll():
    data_rec = vad_audio_out.recv()

    if data_rec == 'speech_start()':
      print 'Speech start'
    if data_rec == 'speech_end()':
      print 'Speech end'

aio_commands.send('stop()')
vad_commands.send('stop()')
aio.join()
vad.join()

print

