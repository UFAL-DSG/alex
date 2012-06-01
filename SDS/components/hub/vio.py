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
from datetime import datetime

import pjsuaxt as pj

import SDS.utils.audio as audio
import SDS.utils.various as various
import SDS.utils.string as string

"""
FIXME: There is confusion in naming packets, frames, and samples.
       Ideally frames should be blocks of samples.

"""

# Logging callback
def log_cb(level, str, len):
    print str,

def get_random_word(wordLen):
  word = ''
  for i in range(wordLen):
    word += random.choice('\0x00ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\xFF')
  return word

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

    self.voipio.on_incoming_call(call.info().remote_uri)

    print "Incoming call from ", call.info().remote_uri

    call_cb = CallCallback(self.cfg, call, self.voipio)
    call.set_callback(call_cb)

    call.answer()

  def wait(self):
    self.sem = threading.Semaphore(0)
    self.sem.acquire()

  def on_reg_state(self):
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

  # Notification when call state has changed
  def on_state(self):
    print "CallCallback::on_state : Call with", self.call.info().remote_uri,
    print "is", self.call.info().state_text,
    print "last code =", self.call.info().last_code,
    print "(" + self.call.info().last_reason + ")"

    if self.call.info().state == pj.CallState.CONNECTING:
      self.voipio.on_call_connecting()
    if self.call.info().state == pj.CallState.CONFIRMED:
      self.voipio.on_call_confirmed()

    if self.call.info().state == pj.CallState.DISCONNECTED:
      pj.Lib.instance().recorder_destroy(self.recorded_id)
      pj.Lib.instance().recorder_destroy(self.played_id)
      self.voipio.on_call_disconnected()

  def on_transfer_status(self, code, reason, final, cont):
    print "CallCallback::on_transfer_status : Call with", self.call.info().remote_uri,
    print "is", self.call.info().state_text,
    print "last code =", self.call.info().last_code,
    print "(" + self.call.info().last_reason + ")"

    print code, reason, final, cont

    return True

  def on_transfer_request(self, dst, code):
    print "CallCallback::on_transfer_request : Remote party transferring the call to ",
    print dst, code

    return 202

  # Notification when call's media state has changed.
  def on_media_state(self):
    if self.call.info().media_state == pj.MediaState.ACTIVE:
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
      print "CallCallback::on_media_state : Media is inactive"

  def on_dtmf_digit(self, digits):
    print "Received digits:", digits


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
    self.audio_record = audio_record
    self.audio_play = audio_play
    self.audio_played = audio_played

    self.output_file_name = os.path.join(self.cfg['Logging']['output_dir'],
                                         'all-'+datetime.now().isoformat('-').replace(':', '-')+'.wav')

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

    while self.commands.poll():
      command = self.commands.recv()

      if command == 'stop()':
        # discard all data in play buffer
        while self.audio_play.poll():
          data_play = self.audio_play.recv()

        return True

      if command == 'flush()':
        # discard all data in play buffer
        while self.audio_play.poll():
          data_play = self.audio_play.recv()

        #self.mem_player.flush()

        return False

      if command.startswith('call('):
        args = string.parse_command(command)
        self.make_call(args['destination'])

        return False

      if command.startswith('transfer('):
        args = string.parse_command(command)
        self.transfer(args['destination'])

        return False

      if command == 'hangup()':
        self.hungup()

        return False


      return False

  def read_write_audio(self):
    """Send some of the available data to the output.
    It should be a non-blocking operation.

    Therefore:
      1) do not send more then play_buffer_frames
      2) send only if stream.get_write_available() is more then the frame size
    """

    if self.audio_play.poll()and self.mem_player.get_write_available() > self.cfg['Audio']['samples_per_frame']*2:
      # send a frame from input to be played
      data_play = self.audio_play.recv()
      if len(data_play) == self.cfg['Audio']['samples_per_frame']*2:
        self.mem_player.put_frame(data_play)

        if self.cfg['VoipIO']['debug']:
          print '.',
          sys.stdout.flush()

    if self.mem_capture.get_read_available() > self.cfg['Audio']['samples_per_frame']*2:
      # get and send recorded data, it must be read at the other end
      data_rec = self.mem_capture.get_frame()
      self.audio_record.send(data_rec)
      if self.cfg['VoipIO']['debug']:
        print '+',
        sys.stdout.flush()


  def get_sip_uri_for_phone_number(self, dst):
    sip_uri = "sip:"+dst+self.cfg['VoipIO']['domain']
    return sip_uri

  def is_sip_uri(self, dst):
    return dst.startswith('sip:')

  def make_call(self, uri):
    try:
        if self.cfg['VoipIO']['debug']:
          print "Making a call to", uri
        return self.acc.make_call(uri, cb=CallCallback())
    except pj.Error, e:
        print "Exception: " + str(e)
        return None

  def transfer(self, uri):
    """FIX: This does not work yet!"""
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
    # FIX a message should be send that there is a new incomming call
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_incoming_call - from ", remote_uri

  def on_call_connecting(self):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_call_connecting"

  def on_call_confirmed(self):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_call_confirmed"

  def on_call_disconnected(self):
    if self.cfg['VoipIO']['debug']:
      print "VoipIO::on_call_disconnected"

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
      print self.cfg['Audio']['samples_per_frame'], media_cfg.audio_frame_ptime
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
        # process all pending commands
        if self.process_pending_commands():
          return

        # process audio data
        self.read_write_audio()

        time.sleep(0.002)

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
