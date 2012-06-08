#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys
import random
import cPickle as pickle

from collections import defaultdict

import __init__

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.tts import TTS
from SDS.components.hub.messages import Command, TTSText
from SDS.utils.mproc import SystemLogger

cfg = {
  'Audio': {
    'sample_rate': 8000,
    'samples_per_frame': 128,
  },
  'VoipIO': {
    'pjsip_log_level': 3,
    'debug': True,
    'reject_calls': True,
    'wait_time_before_calling_back': 10,
    'allowed_phone_numbers': r"(^[234567])",
    'forbidden_phone_number': r"(^112$|^150$|^155$|^156$|^158$)",
    'allowed_users': r"(^[234567])",
    'forbidden_users': r"(^112$|^150$|^155$|^156$|^158$)",
    'allowed_hosts': r"",
    'forbidden_hosts': r"",

#    'domain': 'your_domain',
#    'user': 'your_user',
#    'password': 'your_password',

    'domain': 'your_domain',
    'user': 'your_user',
    'password': 'your_password',
  },
  'VAD': {
    'debug': False,
    'type': 'power',
    'power_threshold': 100,
    'power_threshold_multiplier': 1,
    'power_adaptation_frames': 30,
    'power_decision_frames': 40,
    'power_decision_speech_threshold': 0.7,
    'power_decision_non_speech_threshold': 0.2,
  },
  'TTS': {
    'debug': True,
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
    'system_logger': SystemLogger(stdout = True, output_dir = './call_logs')
  },
  'RepeatAfterMe': {
    'call_db':          'call_db.pckl',
    'sentences_file':   'sentences.txt',
    'ram':             ["Řekněte. ", "Zopakujte. ", "Vyslovte. ", "Zopakujte po mně. ", "Opakujte. ", "Vyslovte. "],
    'introduction':    ["Dobrý den",
                        "Dovolali jste se na telefonní službu Ústavu formální a aplikované lingvistiky",
                        "která pořizuje data pro zlepšování systémů rozpoznávání mluvené řeči",
                        "Systém vás vyzve k opakování jedné nebo více vět",
#                        "Maximální délka hovoru je deset minut",
                        "Pokud budete chtít hovor ukončit, zavěste telefon",
                        "Hovor je nahráván pro výzkumné a komerční účely",
                        "Záznam může být předán jinému subjektu",
                        "Pokud nesouhlasíte, zavěste telefon",
#                        "Děkujeme za spolupráci",
                        ],

    'max_call_length':       10*60,       # in seconds
    'last24_max_num_calls':  20,
    'last24_max_total_time': 50*60,       # in seconds
    'blacklist_for' :        2*60*60,     # in seconds
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

def load_database(file_name):
  db = dict()
  try:
    f = open(file_name, 'r')
    db = pickle.load(f)
    f.close()
  except IOError:
    pass

  if 'calls_from_start_end_length' not in db:
    db['calls_from_start_end_length'] = dict()

  return db

def save_database(file_name, db):
  f = open(file_name, 'w+')
  pickle.dump(db, f)
  f.close()

def get_stats(db, remote_uri):
  num_all_calls = 0
  total_time = 0
  last24_num_calls = 0
  last24_total_time = 0
  try:
    for s, e, l in db['calls_from_start_end_length'][remote_uri]:
      if l > 0:
        num_all_calls += 1
        total_time += l

        # do counts for last 24 hours
        if s > time.time() - 24*60*60:
          last24_num_calls += 1
          last24_total_time += l
  except:
    pass

  return num_all_calls, total_time, last24_num_calls, last24_total_time

def play_intro(cfg, tts_commands, intro_id, last_intro_id):
  for i in range(len(cfg['RepeatAfterMe']['introduction'])):
    last_intro_id = str(intro_id)
    intro_id += 1
    tts_commands.send(Command('synthesize(user_id="%s",text="%s")' % (last_intro_id,
      cfg['RepeatAfterMe']['introduction'][i]), 'HUB', 'TTS'))

  return intro_id, last_intro_id

def ram():
  return random.choice(cfg['RepeatAfterMe']['ram'])

#########################################################################
#########################################################################

cfg['Logging']['system_logger'].info("Repeat After Me dialogue system\n"+
"="*120)

#########################################################################
#########################################################################


sample_sentences = load_sentences(cfg['RepeatAfterMe']['sentences_file'])

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

# init the system
call_start = 0
count_intro = 0
intro_played = False
reject_played = False
intro_id = 0
last_intro_id = -1
end_played = False
s_voice_activity = False
s_last_voice_activity_time = 0
u_voice_activity = False
u_last_voice_activity_time = 0

db = load_database(cfg['RepeatAfterMe']['call_db'])

for remote_uri in db['calls_from_start_end_length']:
  num_all_calls, total_time, last24_num_calls, last24_total_time = get_stats(db, remote_uri)

  m = []
  m.append('')
  m.append('='*120)
  m.append('Remote SIP URI: %s' % remote_uri)
  m.append('-'*120)
  m.append('Total calls:             %d' % num_all_calls)
  m.append('Total time (s):          %f' % total_time)
  m.append('Last 24h total calls:    %d' % last24_num_calls)
  m.append('Last 24h total time (s): %f' % last24_total_time)
  m.append('-'*120)

  current_time = time.time()
  if last24_num_calls > cfg['RepeatAfterMe']['last24_max_num_calls'] or \
    last24_total_time > cfg['RepeatAfterMe']['last24_max_total_time']:

    # add the remote uri to the black list
    vio_commands.send(Command('black_list(remote_uri="%s",expire="%d")' % (remote_uri,
      current_time+cfg['RepeatAfterMe']['blacklist_for']), 'HUB', 'VoipIO'))
    m.append('BLACKLISTED')
  else:
    m.append('OK')

  m.append('-'*120)
  m.append('')
  cfg['Logging']['system_logger'].info('\n'.join(m))

call_back_time = -1
call_back_uri = None

while 1:
  time.sleep(cfg['Hub']['main_loop_sleep_time'])

  if vad_audio_out.poll():
    data_vad = vad_audio_out.recv()


  if call_back_time != -1 and call_back_time < time.time():
    vio_commands.send(Command('make_call(destination="%s")' % call_back_uri, 'HUB', 'VoipIO'))
    call_back_time = -1
    call_back_uri = None

  # read all messages
  if vio_commands.poll():
    command = vio_commands.recv()

    if isinstance(command, Command):
      if command.parsed['__name__'] == "incoming_call":
        cfg['Logging']['system_logger'].info(command)

      if command.parsed['__name__'] == "rejected_call":
        cfg['Logging']['system_logger'].info(command)

        call_back_time = time.time() + cfg['VoipIO']['wait_time_before_calling_back']
        call_back_uri = command.parsed['remote_uri']


      if command.parsed['__name__'] == "rejected_call_from_blacklisted_uri":
        cfg['Logging']['system_logger'].info(command)

        remote_uri = command.parsed['remote_uri']

        num_all_calls, total_time, last24_num_calls, last24_total_time = get_stats(db, remote_uri)

        m = []
        m.append('')
        m.append('='*120)
        m.append('Rejected incoming call from blacklisted URI: %s' % remote_uri)
        m.append('-'*120)
        m.append('Total calls:             %d' % num_all_calls)
        m.append('Total time (s):          %f' % total_time)
        m.append('Last 24h total calls:    %d' % last24_num_calls)
        m.append('Last 24h total time (s): %f' % last24_total_time)
        m.append('='*120)
        m.append('')
        cfg['Logging']['system_logger'].info('\n'.join(m))

      if command.parsed['__name__'] == "call_connecting":
        cfg['Logging']['system_logger'].info(command)

      if command.parsed['__name__'] == "call_confirmed":
        cfg['Logging']['system_logger'].info(command)

        remote_uri = command.parsed['remote_uri']
        num_all_calls, total_time, last24_num_calls, last24_total_time = get_stats(db, remote_uri)

        m = []
        m.append('')
        m.append('='*120)
        m.append('Incoming call from :     %s' % remote_uri)
        m.append('-'*120)
        m.append('Total calls:             %d' % num_all_calls)
        m.append('Total time (s):          %f' % total_time)
        m.append('Last 24h total calls:    %d' % last24_num_calls)
        m.append('Last 24h total time (s): %f' % last24_total_time)
        m.append('-'*120)

        if last24_num_calls > cfg['RepeatAfterMe']['last24_max_num_calls'] or \
          last24_total_time > cfg['RepeatAfterMe']['last24_max_total_time']:

          tts_commands.send(Command('synthesize(text="Děkujeme za zavolání, ale už jste volali hodně. '
          'Prosím zavolejte za dvacet čtyři hodin. Nashledanou.")' , 'HUB', 'TTS'))
          reject_played = True
          s_voice_activity = True
          vio_commands.send(Command('black_list(remote_uri="%s",expire="%d")' % (remote_uri,
            time.time()+cfg['RepeatAfterMe']['blacklist_for']), 'HUB', 'VoipIO'))
          m.append('CALL REJECTED')
        else:
          # init the system
          call_start = time.time()
          count_intro = 0
          intro_played = False
          reject_played = False
          end_played = False
          s_voice_activity = False
          s_last_voice_activity_time = 0
          u_voice_activity = False
          u_last_voice_activity_time = 0

          intro_id, last_intro_id = play_intro(cfg, tts_commands, intro_id, last_intro_id)

          m.append('CALL ACCEPTED')

        m.append('='*120)
        m.append('')
        cfg['Logging']['system_logger'].info('\n'.join(m))

        try:
          db['calls_from_start_end_length'][remote_uri].append([time.time(), 0, 0])
        except:
          db['calls_from_start_end_length'][remote_uri] = [[time.time(), 0, 0], ]
        save_database(cfg['RepeatAfterMe']['call_db'], db)

      if command.parsed['__name__'] == "call_disconnected":
        cfg['Logging']['system_logger'].info(command)
        cfg['Logging']['system_logger'].call_end()

        remote_uri = command.parsed['remote_uri']

        vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
        vad_commands.send(Command('flush()', 'HUB', 'VAD'))
        tts_commands.send(Command('flush()', 'HUB', 'TTS'))

        s, e, l = db['calls_from_start_end_length'][remote_uri][-1]
        db['calls_from_start_end_length'][remote_uri][-1] = [s, time.time(), time.time() - s]
        save_database('call_db.pckl', db)

        intro_played = False

      if command.parsed['__name__'] == "play_utterance_start":
        cfg['Logging']['system_logger'].info(command)
        s_voice_activity = True

      if command.parsed['__name__'] == "play_utterance_end":
        cfg['Logging']['system_logger'].info(command)

        s_voice_activity = False
        s_last_voice_activity_time = time.time()

        if command.parsed['user_id'] == last_intro_id:
          intro_played = True
          s_last_voice_activity_time = 0

  if vad_commands.poll():
    command = vad_commands.recv()
    cfg['Logging']['system_logger'].info(command)

    if isinstance(command, Command):
      if command.parsed['__name__'] == "speech_start":
        u_voice_activity = True
      if command.parsed['__name__'] == "speech_end":
        u_voice_activity = False
        u_last_voice_activity_time = time.time()

  if tts_commands.poll():
    command = tts_commands.recv()
    cfg['Logging']['system_logger'].info(command)

  current_time = time.time()

#  print
#  print intro_played, end_played
#  print s_voice_activity, u_voice_activity,
#  print call_start,  current_time, u_last_voice_activity_time, s_last_voice_activity_time
#  print current_time - s_last_voice_activity_time > 5, u_last_voice_activity_time - s_last_voice_activity_time > 0

  if reject_played == True and s_voice_activity == False:
    # be careful it does not hangup immediately
    reject_played = False
    vio_commands.send(Command('hangup()', 'HUB', 'VoipIO'))
    vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
    vad_commands.send(Command('flush()', 'HUB', 'VoipIO'))
    tts_commands.send(Command('flush()', 'HUB', 'VoipIO'))

  if intro_played and current_time - call_start > cfg['RepeatAfterMe']['max_call_length'] and s_voice_activity == False:
    # hovor trval jiz vice nez deset minut
    if not end_played:
      s_voice_activity = True
      last_intro_id = str(intro_id)
      intro_id += 1
      tts_commands.send(Command('synthesize(text="%s")' % "To bylo všechno. Děkujeme za zavolání.", 'HUB', 'TTS'))
      end_played = True
    else:
      intro_played = False
      # be careful it does not hangup immediately
      vio_commands.send(Command('hangup()', 'HUB', 'VoipIO'))
      vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
      vad_commands.send(Command('flush()', 'HUB', 'VAD'))
      tts_commands.send(Command('flush()', 'HUB', 'TTS'))

  if intro_played and \
     s_voice_activity == False and \
     u_voice_activity == False and \
     current_time - s_last_voice_activity_time > 6 and \
     current_time - u_last_voice_activity_time > 0.6:

    s_voice_activity = True
    s = ram() + ' ' + sample_sentence(sample_sentences)
    tts_commands.send(Command('synthesize(text="%s")' % s, 'HUB', 'TTS'))

    m = []
    m.append('='*120)
    m.append('Say: '+s)
    m.append('='*120)

    cfg['Logging']['system_logger'].info('\n'.join(m))

# stop processes
vio_commands.send(Command('stop()', 'HUB', 'VoipIO'))
vad_commands.send(Command('stop()', 'HUB', 'VAD'))
tts_commands.send(Command('stop()', 'HUB', 'TTS'))

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
