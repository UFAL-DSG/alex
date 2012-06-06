#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys
import random

import __init__

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.tts import TTS
from SDS.components.hub.messages import Command, TTSText

cfg = {
  'Audio': {
    'sample_rate': 8000,
    'samples_per_frame': 128,
  },
  'VoipIO': {
    'pjsip_log_level': 3,
    'debug': False,
    'reject_calls': False,
    'call_back': False,
    'wait_time_before_calling_back': 10,
    'allowed_phone_numbers': r"(^[234567])",
    'forbidden_phone_number': r"(^112$|^150$|^155$|^156$|^158$)",
    'allowed_users': r"(^[234567])",
    'forbidden_users': r"(^112$|^150$|^155$|^156$|^158$)",
    'allowed_hosts': r"",
    'forbidden_hosts': r"",

    'domain': 'your_domain',
    'user': 'your_user',
    'password': 'your_password',
  },
  'VAD': {
    'debug': False,
    'type': 'power',
    'power_threshold': 190,
    'power_threshold_multiplier': 1,
    'power_adaptation_frames': 30,
    'power_decision_frames': 40,
    'power_decision_speech_threshold': 0.7,
    'power_decision_non_speech_threshold': 0.2,
  },
  'TTS': {
    'debug': False,
    'type': 'Google',
    'Google' : {
      'debug': False,
      'language' : 'cs'
    }
  },
  'Hub': {
    'main_loop_sleep_time': 0.005,
  },
  'Logging': {
    'output_dir' : './call_logs'
  }
}

def load_sentences(file_name):
  f = open(file_name, 'r')

  r = []
  for s in f:
    s = s.strip()
    r.append(s)

  f.close()

  return r

def sample_sentence(l):
  return random.choice(l)

introduction_cs = ["Dobrý den",
#"Dovolali jste se na telefonní službu Ústavu formální a aplikované lingvistiky",
#"která pořizuje data pro zlepšování systémů rozpoznávání mluvené řeči",
#"Systém vás vyzve k opakování jedné nebo více vět",
#"Maximální délka hovoru je deset minut",
#"Pokud budete chtít hovor ukončit, zavěste telefon",
"Hovor je nahráván pro výzkumné a komerční účely",
"Záznam může být předán jinému subjektu",
"Pokud nesouhlasíte, potom zavěste",
"Děkujeme za spolupráci",
]

def play_intro(tts_commands, intro_id, last_intro_id):
  for i in range(len(introduction_cs)):
    last_intro_id = str(intro_id)
    intro_id += 1
    tts_commands.send(Command('synthesize(user_id="%s",text="%s")' % (last_intro_id, introduction_cs[i]), 'HUB', 'TTS'))

  return intro_id, last_intro_id

def ram():
  return random.choice(["Řekněte ", "Zopakujte ", "Vyslovte ", "Zopakujte po mně", "Opakujte", "Vyslovte"])

print "Repeat After Me dialogue system"
print "="*120

ss = load_sentences('mkp_rur_matka.txt')

vio_commands, vio_child_commands = multiprocessing.Pipe() # used to send commands to VoipIO
vio_record, vio_child_record = multiprocessing.Pipe()     # I read from this connection recorded audio
vio_play, vio_child_play = multiprocessing.Pipe()         # I write in audio to be played
vio_played, vio_child_played = multiprocessing.Pipe()     # I read from this to get played audio
                                                          #   which in sync with recorded signal

vad_commands, vad_child_commands = multiprocessing.Pipe() # used to send commands to VAD
vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

tts_commands, tts_child_commands = multiprocessing.Pipe() # used to send commands to TTS
tts_text_in, tts_child_text_in = multiprocessing.Pipe()   # used to send TTS text

command_connections = [vio_commands, vad_commands, tts_commands]

non_command_connections = [vio_record, vio_child_record,
                           vio_play, vio_child_play,
                           vio_played, vio_child_played,
                           vad_audio_out, vad_child_audio_out,
                           tts_text_in, tts_child_text_in]

vio = VoipIO(cfg, vio_child_commands, vio_child_record, vio_child_play, vio_child_played)
vad = VAD(cfg, vad_child_commands, vio_record, vio_played, vad_child_audio_out)
tts = TTS(cfg, tts_child_commands, tts_child_text_in, vio_play)

vio.start()
vad.start()
tts.start()

# init the constants
max_intro = len(introduction_cs)
max_call_length = 10*60

# init the system
call_start = 0
count_intro = 0
intro_played = False
intro_id = 0
last_intro_id = -1
end_played = False
s_voice_activity = False
s_last_voice_activity_time = 0
u_voice_activity = False
u_last_voice_activity_time = 0

while 1:
  time.sleep(cfg['Hub']['main_loop_sleep_time'])

  if vad_audio_out.poll():
    data_vad = vad_audio_out.recv()

  # read all messages
  if vio_commands.poll():
    command = vio_commands.recv()
    print
    print command
    print

    if isinstance(command, Command):
      if command.parsed['__name__'] == "call_confirmed":
        # init the system
        call_start = time.time()
        count_intro = 0
        intro_played = False
        end_played = False
        s_voice_activity = False
        s_last_voice_activity_time = 0
        u_voice_activity = False
        u_last_voice_activity_time = 0

        intro_id, last_intro_id = play_intro(tts_commands, intro_id, last_intro_id)

      if command.parsed['__name__'] == "call_disconnected":
        vio_commands.send(Command('flush()'))
        vad_commands.send(Command('flush()'))
        tts_commands.send(Command('flush()'))

      if command.parsed['__name__'] == "play_utterance_start":
        s_voice_activity = True

      if command.parsed['__name__'] == "play_utterance_end":
        s_voice_activity = False
        s_last_voice_activity_time = time.time()

        if command.parsed['user_id'] == last_intro_id:
          intro_played = True
          s_last_voice_activity_time = 0

  if vad_commands.poll():
    command = vad_commands.recv()
    print
    print command
    print

    if isinstance(command, Command):
      if command.parsed['__name__'] == "speech_start":
        u_voice_activity = True
      if command.parsed['__name__'] == "speech_end":
        u_voice_activity = False
        u_last_voice_activity_time = time.time()

  if tts_commands.poll():
    command = tts_commands.recv()
    print
    print command
    print

  current_time = time.time()

#  print
#  print intro_played, end_played
#  print s_voice_activity, u_voice_activity,
#  print call_start,  current_time, u_last_voice_activity_time, s_last_voice_activity_time
#  print current_time - s_last_voice_activity_time > 5, u_last_voice_activity_time - s_last_voice_activity_time > 0

  if intro_played and current_time - call_start > max_call_length and s_voice_activity == False:
    # hovor trval jiz vice nez deset minut
    if not end_played:
      s_voice_activity = True
      last_intro_id = str(intro_id)
      intro_id += 1
      tts_commands.send(Command('synthesize(text="%s")' % "Uplynulo deset minut. Děkujeme za zavolání.", 'HUB', 'TTS'))
      end_played = True
    else:
      intro_played = False
      # be careful it does not hangup immediately
      vio_commands.send(Command('hangup()', 'HUB', 'VoipIO'))
      vio_commands.send(Command('flush()'))
      vad_commands.send(Command('flush()'))
      tts_commands.send(Command('flush()'))

  if intro_played and \
     s_voice_activity == False and \
     u_voice_activity == False and \
     (current_time - s_last_voice_activity_time > 6 or u_last_voice_activity_time - s_last_voice_activity_time > 0):

    s_voice_activity = True
    s = ram()
    print
    print '='*80
    print 'Say:', s, '-',
    tts_commands.send(Command('synthesize(text="%s")' % s, 'HUB', 'TTS'))
    s = sample_sentence(ss)
    print s
    print '='*80
    print
    tts_commands.send(Command('synthesize(text="%s")' % s, 'HUB', 'TTS'))


# stop processes
vio_commands.send(Command('stop()'))
vad_commands.send(Command('stop()'))
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
tts.join()

print
