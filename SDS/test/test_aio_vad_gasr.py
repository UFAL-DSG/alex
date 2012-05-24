#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time

from __init__ import init_path

init_path()

import SDS.utils.audio as audio
import SDS.utils.various as various

from SDS.components.hub.aio import AudioIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.asr import ASR

cfg = {
  'Audio': {
      'sample_rate': 8000
  },
  'AudioIO': {
    'debug': False,
    'samples_per_buffer': 80,
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
  'ASR': {
    'debug': True,
    'type': 'Google',
    'Google': {
      'debug': False,
      'language' : 'en'
    }
  },
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the AudioIO, VAD and ASR components:"
print "="*120

wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
# split audio into frames
wav = various.split_to_bins(wav, 2*cfg['AudioIO']['samples_per_buffer'])
# remove the last frame

aio_commands, aio_child_commands = multiprocessing.Pipe() # used to send commands to AudioIO
aio_record, aio_child_record = multiprocessing.Pipe()     # I read from this connection recorded audio
aio_play, aio_child_play = multiprocessing.Pipe()         # I write in audio to be played
aio_played, aio_child_played = multiprocessing.Pipe()     # I read from this to get played audio
                                                          #   which in sync with recorded signal

vad_commands, vad_child_commands = multiprocessing.Pipe() # used to send commands to VAD
vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

asr_commands, asr_child_commands = multiprocessing.Pipe() # used to send commands to ASR
asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe() # used to read ASR hypotheses

aio = AudioIO(cfg, aio_child_commands, aio_child_record, aio_child_play, aio_child_played)
vad = VAD(cfg, vad_child_commands, aio_record, aio_played, vad_child_audio_out)
asr = ASR(cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses)

non_command_connections = [aio_record, aio_child_record,
                           aio_play, aio_child_play,
                           aio_played, aio_child_played,
                           vad_audio_out, vad_child_audio_out,
                           asr_hypotheses_out, asr_child_hypotheses]

aio.start()
vad.start()
asr.start()

count = 0
max_count = 5000
while count < max_count:
  time.sleep(0.002)
  count += 1

  # write one frame into the audio output
  if wav:
    data_play = wav.pop(0)
    #print len(wav), len(data_play)
    aio_play.send(data_play)

  # read all ASR output audio
  while asr_hypotheses_out.poll():
    data_hyp = asr_hypotheses_out.recv()

    print data_hyp

# stop processes
aio_commands.send('stop()')
vad_commands.send('stop()')
asr_commands.send('stop()')

# clean connections
for c in non_command_connections:
  while c.poll():
    c.recv()

# wait for processes to stop
aio.join()
vad.join()
asr.join()

print


