#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyaudio
import wave
import time
import random
import multiprocessing
import sys
import os.path
import struct
import array
import threading
import re
import pjsuaxt as pj

from datetime import datetime
from collections import deque

import SDS.utils.audio as audio
import SDS.utils.various as various
import SDS.utils.string as string

from SDS.components.hub.messages import Command, Frame
from SDS.utils.exception import VoipIOException

# Logging callback
def log_cb(level, str, len):
    print str,

class AccountCallback(pj.AccountCallback):
  """ Callback to receive events from account

  """

  sem = None
  voipio = None

  def __init__(self, cfg, account=None, voipio=None):
    pj.AccountCallback.__init__(self, account)

    self.cfg = cfg
    self.voipio = voipio

  def on_incoming_call(self, call):
    """ Notification on incoming call
    """

    if not self.cfg['VoipIO']['reject_calls']:
      self.voipio.on_incoming_call(call.info().remote_uri)

      if self.cfg['VoipIO']['debug']:
        print "Incoming call from ", call.info().remote_uri

      call_cb = CallCallback(self.cfg, call, self.voipio)
      call.set_callback(call_cb)

      call.answer()
    else:
      remote_uri = call.info().remote_uri
      
      if self.cfg['VoipIO']['debug']:
        print "Rejected call from ", remote_uri
        
      # respond by "Busy here"
      call.answer(486)

      self.voipio.on_rejected_call(remote_uri)

  def wait(self):
    """Wait for the registration to finish.
    """

    self.sem = threading.Semaphore(0)
    self.sem.acquire()

  def on_reg_state(self):
    """Stop waiting if the registration process ended.
    """

    if self.sem:
      if self.account.info().reg_status >= 200:
        self.sem.release()

class CallCallback(pj.CallCallback):
  """ Callback to receive events from Call
  """

  def __init__(self, cfg, call=None, voipio=None):
    pj.CallCallback.__init__(self, call)

    self.cfg = cfg
    self.voipio = voipio

    self.rec_id = None
    self.output_file_name_recorded = os.path.join(self.cfg['Logging']['output_dir'],
      'all-'+datetime.now().isoformat('-').replace(':', '-')+'.recorded.wav')
    self.output_file_name_played = os.path.join(self.cfg['Logging']['output_dir'],
      'all-'+datetime.now().isoformat('-').replace(':', '-')+'.played.wav')

    self.recorded_id = None
    self.played_id = None

  # Notification when call state has changed
  def on_state(self):
    if self.cfg['VoipIO']['debug']:
      print "CallCallback::on_state : Call with", self.call.info().remote_uri,
      print "is", self.call.info().state_text,
      print "last code =", self.call.info().last_code,
      print "(" + self.call.info().last_reason + ")"

    if self.call.info().state == pj.CallState.CONNECTING:
      self.voipio.on_call_connecting()
    if self.call.info().state == pj.CallState.CONFIRMED:
      self.voipio.on_call_confirmed()

    if self.call.info().state == pj.CallState.DISCONNECTED:
      if self.recorded_id:
        pj.Lib.instance().recorder_destroy(self.recorded_id)
      if self.played_id:
        pj.Lib.instance().recorder_destroy(self.played_id)
      self.voipio.on_call_disconnected()

  def on_transfer_status(self, code, reason, final, cont):
    if self.cfg['VoipIO']['debug']:
      print "CallCallback::on_transfer_status : Call with", self.call.info().remote_uri,
      print "is", self.call.info().state_text,
      print "last code =", self.call.info().last_code,
      print "(" + self.call.info().last_reason + ")"

    print code, reason, final, cont

    return True

  def on_transfer_request(self, dst, code):
    if self.cfg['VoipIO']['debug']:
      print "CallCallback::on_transfer_request : Remote party transferring the call to ",
      print dst, code

    return 202

  # Notification when call's media state has changed.
  def on_media_state(self):
    if self.call.info().media_state == pj.MediaState.ACTIVE:
      if self.cfg['VoipIO']['debug']:
        print "CallCallback::on_media_state : Media is now active"
        
      if not self.rec_id:
        call_slot = self.call.info().conf_slot

        # Create wave recorders
        self.recorded_id = pj.Lib.instance().create_recorder(self.output_file_name_recorded)
        recorded_slot = pj.Lib.instance().recorder_get_slot(self.recorded_id)
        self.played_id = pj.Lib.instance().create_recorder(self.output_file_name_played)
        played_slot = pj.Lib.instance().recorder_get_slot(self.played_id)

        # Connect the call to the wave recorder
        pj.Lib.instance().conf_connect(call_slot, recorded_slot)
        # Connect the memory player to the wave recorder
        pj.Lib.instance().conf_connect(self.voipio.mem_player.port_slot, played_slot)

        # Connect the call to the memory capture
        pj.Lib.instance().conf_connect(call_slot, self.voipio.mem_capture.port_slot)
        # Connect the memory player to the call
        pj.Lib.instance().conf_connect(self.voipio.mem_player.port_slot, call_slot)
    else:
      if self.cfg['VoipIO']['debug']:
        print "CallCallback::on_media_state : Media is inactive"

  def on_dtmf_digit(self, digits):
    if self.cfg['VoipIO']['debug']:
      print "Received digits:", digits
      
    self.voipio.on_dtmf_digit(digits)



class VoipIO(multiprocessing.Process):
  """ VoipIO implements IO operations using a SIP protocol.

  If enabled then it logs all recorded and played audio into a file.
  The file is in RIFF wave in stereo, where left channel contains recorded audio and the right channel contains
  played audio.
  """

  def __init__(self, cfg, commands, audio_record, audio_play, audio_played):
    """ Initialize VoipIO

    cfg - configuration dictionary

    audio_record - inter-process connection for sending recorded audio.
      Audio is divided into frames, each with the length of samples_per_frame.

    audio_play - inter-process connection for receiving audio which should to be played.
      Audio must be divided into frames, each with the length of samples_per_frame.

    audio_played - inter-process connection for sending audio which was played.
      Audio is divided into frames and synchronised with the recorded audio.
    """

    multiprocessing.Process.__init__(self)

    self.cfg = cfg
    
    self.commands = commands
    self.local_commands = deque()
    
    self.audio_record = audio_record
    
    self.audio_play = audio_play
    self.local_audio_play = deque()
    
    self.audio_played = audio_played
    
    self.last_frame_id = 1
    self.message_queue = []

    self.output_file_name = os.path.join(self.cfg['Logging']['output_dir'],
                                         'all-'+datetime.now().isoformat('-').replace(':', '-')+'.wav')

  def recv_input_localy(self):
    """ Copy all input from input connections into local queue objects.
    
    This will prevent blocking the senders.
    """
    
    while self.commands.poll():
      command = self.commands.recv()
      self.local_commands.append(command)

    while self.audio_play.poll():
      frame = self.audio_play.recv()
      self.local_audio_play.append(frame)
  
  def process_pending_commands(self):
    """Process all pending commands.

    Available commands:
      stop()    - stop processing and exit the process
      flush()   - flush input buffers.
        Now it only flushes the input connection.
        It is not able flush data already send to the sound card.

      call(dst)     - make a call to the destination dst
      transfer(dst) - transfer the existing call to the destination dst
      hungup()      - hung up the existing call

    Return True if the process should terminate.

    """

    if self.local_commands:
      command = self.local_commands.popleft()
      if isinstance(command, Command):
        if command.parsed['__name__'] == 'stop':
          # discard all data in play buffer
          while self.audio_play.poll():
            data_play = self.audio_play.recv()

          return True

        if command.parsed['__name__'] == 'flush':
          # discard all data in play buffer
          while self.audio_play.poll():
            data_play = self.audio_play.recv()

          self.local_commands.clear()
          self.local_audio_play.clear()
          
          self.mem_player.flush()

          return False

        if command.parsed['__name__'] == 'make_call':
          self.make_call(command.parsed['destination'])

          return False

        if command.parsed['__name__'] == 'transfer':
          self.transfer(command.parsed['destination'])

          return False

        if command.parsed['__name__'] == 'hangup':
          self.hungup()

          return False

        raise VoipIOException('Unsupported command: ' + command)
        
    return False

  def send_pending_messages(self):
    """ Send all messages for which corresponding frame was already played.
    """
    num_played_frames = self.mem_player.get_num_played_frames()

    del_messages = []

    for i, (message, frame_id) in enumerate(self.message_queue):
      if frame_id <= num_played_frames:
        self.commands.send(message)
        del_messages.append(frame_id)

    # delete the messages which were already sent
    self.message_queue = [x for x in self.message_queue if x[1] not in del_messages]

  def read_write_audio(self):
    """Send some of the available data to the output.
    
    It should be a non-blocking operation.
    """

    if self.local_audio_play and self.mem_player.get_write_available() > self.cfg['Audio']['samples_per_frame']*2:
      # send a frame from input to be played
      data_play = self.local_audio_play.popleft()

      if isinstance(data_play, Frame):
        if len(data_play) == self.cfg['Audio']['samples_per_frame']*2:
          self.last_frame_id = self.mem_player.put_frame(data_play.payload)

          if self.cfg['VoipIO']['debug']:
            print '.',
            sys.stdout.flush()

          # send played audio
          self.audio_played.send(data_play)

      elif isinstance(data_play, Command):
        if data_play.parsed['__name__'] == 'utterance_start':
          self.message_queue.append((Command('play_utterance_start(id="%s")' % data_play.parsed['id'], 'VoipIO', 'HUB'), self.last_frame_id))
        if data_play.parsed['__name__'] == 'utterance_end':
          self.message_queue.append((Command('play_utterance_end(id="%s")' % data_play.parsed['id'], 'VoipIO', 'HUB'), self.last_frame_id))

    if self.mem_capture.get_read_available() > self.cfg['Audio']['samples_per_frame']*2:
      # get and send recorded data, it must be read at the other end
      data_rec = self.mem_capture.get_frame()
      self.audio_record.send(Frame(data_rec))

      if self.cfg['VoipIO']['debug']:
        print ',',
        sys.stdout.flush()

  def is_sip_uri(self, dst):
    """ Check whether it is a SIP URI.
    """
    return dst.startswith('sip:')

  def has_sip_uri(self, dst):
    p = re.search(r'(sip:[a-zA-Z0-9_\.]+@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?)', dst)
    if not p:
      return False

    return True

  def get_sip_uri(self, dst):
    p = re.search(r'(sip:[a-zA-Z0-9_\.]+@[a-zA-Z0-9_\.]+(:[0-9]{1,4})?)', dst)
    if not p:
      return None

    return p.group(0)

  def is_phone_number(self, dst):
    """ Check whether it is a phone number.
    """
    p = re.search('(^\+?[0-9]{1,12}$)', dst)
    if not p:
      return False

    return True

  def construct_sip_uri_from_phone_number(self, dst):
    """ Construct a valid SIP URI for given phone number.
    """
    sip_uri = "sip:"+dst+'@'+self.cfg['VoipIO']['domain']
    return sip_uri

  def is_accepted_phone_number(self, dst):
    """ Check the phone number against the positive and negative patterns.
    """

    if self.cfg['VoipIO']['allowed_phone_numbers']:
      p = re.search(self.cfg['VoipIO']['allowed_phone_numbers'], dst)
      if not p:
        return False

    if self.cfg['VoipIO']['forbidden_phone_number']:
      p = re.search(self.cfg['VoipIO']['forbidden_phone_number'], dst)
      if p:
        return False

    return True

  def is_accepted_sip_uri(self, dst):
    """ Check the SIP URI against the positive and negative patterns.
    """

    sip_uri = pj.SIPUri(dst)
    
    if self.cfg['VoipIO']['allowed_users']:
      p = re.search(self.cfg['VoipIO']['allowed_users'], sip_uri.user)
      if not p:
        return False
    
    if self.cfg['VoipIO']['forbidden_users']:
      p = re.search(self.cfg['VoipIO']['forbidden_users'], sip_uri.user)
      if p:
        return False

    if self.cfg['VoipIO']['allowed_hosts']:
      p = re.search(self.cfg['VoipIO']['allowed_hosts'], sip_uri.host)
      if not p:
        return False

    if self.cfg['VoipIO']['forbidden_hosts']:
      p = re.search(self.cfg['VoipIO']['forbidden_hosts'], sip_uri.host)
      if p:
        return False

    return True

  def escape_sip_uri(self, uri):
    uri = uri.replace('"', "'")
    uri = uri.replace(' ', "_")
    uri = uri.replace('/', "_")
    uri = uri.replace('\\', "_")

    return uri

  def normalize_uri(self, uri):
    """ Normalize the phone number or sip uri with a contact name into a clear SIP URI.
    """
    
    if self.is_phone_number(uri):
      if self.is_accepted_phone_number(uri):
        uri = self.construct_sip_uri_from_phone_number(uri)
      else:
        return "blocked"
    elif self.has_sip_uri(uri):
      uri = self.get_sip_uri(uri)
      if self.is_accepted_sip_uri(uri):
        uri = self.get_sip_uri(uri)
      else:
        return "blocked"
        
    return uri

  def make_call(self, uri):
    """ Call privided URI. Check whether it is allowed.
    """
    try:
      uri = self.normalize_uri(uri)
      
      if self.cfg['VoipIO']['debug']:
        print "Making a call to", uri
        
      if self.is_sip_uri(uri):
        # create a call back for the call
        call_cb = CallCallback(self.cfg, None, self)
        return self.acc.make_call(uri, cb=call_cb)
      elif uri == "blocked":
        if self.cfg['VoipIO']['debug']:
          print 'VoipIO : Blocked call to a forbidden phone number -', uri
          sys.stdout.flush()
      else:
        raise VoipIOException('Making call to SIP URI which is not SIP URI - ' + uri)

    except pj.Error, e:
      print "Exception: " + str(e)
      return None

  def transfer(self, uri):
    """FIXME: This does not work yet!"""
    return
    
    try:
      if self.cfg['VoipIO']['debug']:
        print "Transferring the call to", uri
      return self.call.transfer(uri)
    except pj.Error, e:
      print "Exception: " + str(e)
      return None

  def hangup(self):
    try:
      if self.cfg['VoipIO']['debug']:
        print "Hung up the call"
      return self.call.hungup()
    except pj.Error, e:
      print "Exception: " + str(e)
      return None

  def on_incoming_call(self, remote_uri):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_incoming_call - from ", remote_uri

    # send a message that there is a new incoming call
    self.commands.send(Command('incoming_call(remote_uri="%s")' % self.escape_sip_uri(remote_uri), 'VoipIO', 'HUB'))

  def on_rejected_call(self, remote_uri):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_rejected_call - from ", remote_uri

    # send a message that we rejected an incoming call
    self.commands.send(Command('rejected_call(remote_uri="%s")' % self.escape_sip_uri(remote_uri), 'VoipIO', 'HUB'))

    if self.cfg['VoipIO']['call_back']:
      # wait for all SIP messages to be send
      time.sleep(self.cfg['VoipIO']['wait_time_before_calling_back'])

      # call back to the caller
      # use the queue since we cannot make calls from a callback
      self.local_commands.append(Command('make_call(destination="%s")' % self.escape_sip_uri(remote_uri), 'VoipIO', 'VoipIO'))

  def on_call_connecting(self):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_call_connecting"

    # send a message that the call is connecting
    self.commands.send(Command('call_connecting()', 'VoipIO', 'HUB'))

  def on_call_confirmed(self):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_call_confirmed"

    # send a message that the call is confirmed
    self.commands.send(Command('call_confirmed()', 'VoipIO', 'HUB'))

  def on_call_disconnected(self):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_call_disconnected"

    # send a message that the call is disconnected
    self.commands.send(Command('call_disconnected()', 'VoipIO', 'HUB'))

  def on_dtmf_digit(self, digits):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_dtmf_digit"

    # send a message that a digit was recieved
    self.commands.send(Command('dtmf_digit(digit="%s")' % digits, 'VoipIO', 'HUB'))

  def run(self):
    try:
      # Create library instance
      self.lib = pj.Lib()

      # Init library with default config with some customization.

      ua_cfg = pj.UAConfig()
      ua_cfg.max_calls = 1

      log_cfg = pj.LogConfig()
      log_cfg.level = self.cfg['VoipIO']['pjsip_log_level']
      log_cfg.callback = log_cb

      media_cfg = pj.MediaConfig()
      media_cfg.clock_rate = self.cfg['Audio']['sample_rate']
      media_cfg.audio_frame_ptime = int(1000*self.cfg['Audio']['samples_per_frame']/self.cfg['Audio']['sample_rate'])
      media_cfg.no_vad = True
      media_cfg.enable_ice = False

      self.lib.init(ua_cfg, log_cfg, media_cfg)
      self.lib.set_null_snd_dev()

      # Create UDP transport which listens to any available port
      self.transport = self.lib.create_transport(pj.TransportType.UDP, pj.TransportConfig(0))
      print
      print "Listening on", self.transport.info().host,
      print "port", self.transport.info().port, "\n"

      # Start the library
      self.lib.start()

      self.acc = self.lib.create_account(pj.AccountConfig(self.cfg['VoipIO']['domain'],
                                                          self.cfg['VoipIO']['user'],
                                                          self.cfg['VoipIO']['password']))

      self.acc_cb = AccountCallback(self.cfg, self.acc, self)
      self.acc.set_callback(self.acc_cb)
      self.acc_cb.wait()

      print
      print
      print "Registration complete, status=", self.acc.info().reg_status,  "(" + self.acc.info().reg_reason + ")"

      my_sip_uri = "sip:" + self.transport.info().host + ":" + str(self.transport.info().port)

      # Create memory player
      self.mem_player = pj.MemPlayer(pj.Lib.instance(), self.cfg['Audio']['sample_rate'])
      self.mem_player.create()

      # Create memory capture
      self.mem_capture = pj.MemCapture(pj.Lib.instance(), self.cfg['Audio']['sample_rate'])
      self.mem_capture.create()

      while 1:
        time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

        self.recv_input_localy()
        
        # process all pending commands
        if self.process_pending_commands():
          return

        # send all pending messages which has to be synchronized with played frames
        self.send_pending_messages()
        
        # process audio data
        self.read_write_audio()


      # Shutdown the library
      self.transport = None
      self.acc.delete()
      self.acc = None
      self.lib.destroy()
      self.lib = None

    except pj.Error, e:
      print "Exception: " + str(e)
      self.lib.destroy()
      self.lib = None
