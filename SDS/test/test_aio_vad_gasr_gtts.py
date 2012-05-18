#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import sys
import time
import os.path

__depth__ = 2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), *__depth__*[os.path.pardir])))

import SDS.utils.audio as audio
import SDS.utils.various as various

from SDS.components.hub.aio import AudioIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.asr import ASR
from SDS.components.hub.tts import TTS

cfg = {
  'Audio': {
    'sample_rate': 16000
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
  'TTS': {
    'debug': True,
    'type': 'Google',
    'Google' : {
      'debug': False,
      'language' : 'en'
    }
  },
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the AudioIO, VAD, ASR and TTS components:"
print "="*120

aio_commands, aio_child_commands = multiprocessing.Pipe() # used to send commands to AudioIO
aio_record, aio_child_record = multiprocessing.Pipe()     # I read from this connection recorded audio
aio_play, aio_child_play = multiprocessing.Pipe()         # I write in audio to be played
aio_played, aio_child_played = multiprocessing.Pipe()     # I read from this to get played audio
                                                          #   which in sync with recorded signal

vad_commands, vad_child_commands = multiprocessing.Pipe() # used to send commands to VAD
vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

asr_commands, asr_child_commands = multiprocessing.Pipe() # used to send commands to ASR
asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe() # used to read ASR hypotheses

tts_commands, tts_child_commands = multiprocessing.Pipe() # used to send commands to TTS
tts_text_in, tts_child_text_in = multiprocessing.Pipe()   # used to send TTS text

non_command_connections = [aio_record, aio_child_record,
                           aio_play, aio_child_play,
                           aio_played, aio_child_played,
                           vad_audio_out, vad_child_audio_out,
                           asr_hypotheses_out, asr_child_hypotheses,
                           tts_text_in, tts_child_text_in]

aio = AudioIO(cfg, aio_child_commands, aio_child_record, aio_child_play, aio_child_played)
vad = VAD(cfg, vad_child_commands, aio_record, aio_played, vad_child_audio_out)
asr = ASR(cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses)
tts = TTS(cfg, tts_child_commands, tts_child_text_in, aio_play)

aio.start()
vad.start()
asr.start()
tts.start()

tts_text_in.send('Say something and the recognized text will be played back.')

count = 0
max_count = 1500
while count < max_count:
  time.sleep(0.02)
  count += 1

  if asr_hypotheses_out.poll():
    data_hyp = asr_hypotheses_out.recv()

    if len(data_hyp):
      print data_hyp
      # get top hypotheses text

      top_text = data_hyp[0][1]

      tts_text_in.send('Recognized text: ' + top_text)
    else:
      # nothing was recognised
      print 'Nothing was recognised.'

# stop processes
aio_commands.send('stop()')
vad_commands.send('stop()')
asr_commands.send('stop()')
tts_commands.send('stop()')

# clean connections
for c in non_command_connections:
  while c.poll():
    c.recv()

# wait for processes to stop
aio.join()
vad.join()
asr.join()
tts.join()

print
