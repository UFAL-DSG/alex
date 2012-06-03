#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys

import __init__

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.asr import ASR
from SDS.components.hub.tts import TTS
from SDS.components.hub.messages import Command, TTSText

cfg = {
  'Audio': {
    'sample_rate': 8000, 
    'samples_per_frame': 128,
  },
  'VoipIO': {
    'pjsip_log_level': 3,
    'debug': True,

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
  'ASR': {
    'debug': False,
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
  'Hub': {
    'main_loop_sleep_time': 0.005,
  }, 
  'Logging': {
    'output_dir' : './tmp'
  }
}

print "Test of the AudioIO, VAD, ASR and TTS components:"
print "="*120

vio_commands, vio_child_commands = multiprocessing.Pipe() # used to send commands to VoipIO
vio_record, vio_child_record = multiprocessing.Pipe()     # I read from this connection recorded audio
vio_play, vio_child_play = multiprocessing.Pipe()         # I write in audio to be played
vio_played, vio_child_played = multiprocessing.Pipe()     # I read from this to get played audio
                                                          #   which in sync with recorded signal

vad_commands, vad_child_commands = multiprocessing.Pipe() # used to send commands to VAD
vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

asr_commands, asr_child_commands = multiprocessing.Pipe() # used to send commands to ASR
asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe() # used to read ASR hypotheses

tts_commands, tts_child_commands = multiprocessing.Pipe() # used to send commands to TTS
tts_text_in, tts_child_text_in = multiprocessing.Pipe()   # used to send TTS text

command_connections = [vio_commands, vad_commands, asr_commands, tts_commands]

non_command_connections = [vio_record, vio_child_record,
                           vio_play, vio_child_play,
                           vio_played, vio_child_played,
                           vad_audio_out, vad_child_audio_out,
                           asr_hypotheses_out, asr_child_hypotheses,
                           tts_text_in, tts_child_text_in]

vio = VoipIO(cfg, vio_child_commands, vio_child_record, vio_child_play, vio_child_played)
vad = VAD(cfg, vad_child_commands, vio_record, vio_played, vad_child_audio_out)
asr = ASR(cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses)
tts = TTS(cfg, tts_child_commands, tts_child_text_in, vio_play)

vio.start()
vad.start()
asr.start()
tts.start()

tts_text_in.send(TTSText('Say something and the recognized text will be played back.'))

count = 0
max_count = 50000
while count < max_count:
  time.sleep(cfg['Hub']['main_loop_sleep_time'])
  count += 1

  if asr_hypotheses_out.poll():
    asr_hyp = asr_hypotheses_out.recv()

    if isinstance(asr_hyp.hyp, ASRHyp):
      if len(asr_hyp.hyp):
        print asr_hyp.hyp
        
        # get top hypotheses text
        top_text = asr_hyp.hyp[0][1]

        tts_text_in.send(TTSText('Recognized text: ' + top_text))
      else:
        # nothing was recognised
        print 'Nothing was recognised.'

  # read all messages
  for c in command_connections:
    if c.poll():
      command = c.recv()
      print
      print command
      print
      
# stop processes
vio_commands.send(Command('stop()'))
vad_commands.send(Command('stop()'))
asr_commands.send(Command('stop()'))
tts_commands.send(Command('stop()'))

# clean connections
for c in command_connections:
  while c.poll():
    c.recv()

for c in non_command_connections:
  while c.poll():
    c.recv()

# wait for processes to stop
vio.join()
vad.join()
asr.join()
tts.join()

print
