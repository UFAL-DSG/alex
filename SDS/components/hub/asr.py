#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import sys

import SDS.components.asr.google as GASR

from SDS.utils.exception import SDSException

class ASRException(SDSException):
  pass

class ASR(multiprocessing.Process):
  """ ASR recognizes input audio and returns N-best list hypothesis or a confusion network.

  Recognition starts with the "speech_start()" command in the input audio stream and ends
  with the "speech_end()" command.

  When the "speech_end()" command is received, the component asks responsible ASR module
  to return hypotheses and sends them to the output.

  This component is a wrapper around multiple recognition engines which handles multiprocessing
  communication.
  """

  def __init__(self, cfg, commands, audio_in, hypotheses_out):
    multiprocessing.Process.__init__(self)

    self.cfg = cfg
    self.commands = commands
    self.audio_in = audio_in
    self.hypotheses_out = hypotheses_out

    self.asr = None
    if self.cfg['ASR']['type'] == 'Google':
      self.asr = GASR.GoogleASR(cfg)
    else:
      raise ASRException('Unsupported ASR engine: %s' % (self.cfg['ASR']['type'], ))

  def process_pending_commands(self):
    """Process all pending commands.

    Available aio_com:
      stop() - stop processing and exit the process
      flush() - flush input buffers.
        Now it only flushes the input connection.

    Return True if the process should terminate.
    """

    while self.commands.poll():
      command = self.commands.recv()

      if command == 'stop()':
        return True

      if command == 'flush()':
        # discard all data in in input buffers
        while self.audio_in.poll():
          data_in = self.audio_in.recv()

        self.asr.flush()

        return False

  def read_audio_write_asr_hypotheses(self):
    # read input audio
    while self.audio_in.poll():
      # read recorded audio
      data_rec = self.audio_in.recv()

      dr_speech_start = False
      if data_rec == "speech_start()":
        dr_speech_start = "speech_start()"
      elif data_rec == "speech_end()":
        dr_speech_start = "speech_end()"

      # check consistency of the input command
      if dr_speech_start:
        if not ( (self.speech_start == False and dr_speech_start == "speech_start()") or
                 (self.speech_start == "speech_start()" and dr_speech_start == "speech_end()")
               ):
          raise ASRException('Commands received by ASR components are inconsistent - last command: %s - new command: %s' % (self.speech_start, data_rec))

      if data_rec == "speech_start()":
        self.speech_start = "speech_start()"

        if self.cfg['ASR']['debug']:
          print 'ASR: speech_start()'
          sys.stdout.flush()

      elif data_rec == "speech_end()":
        self.speech_start = False

        if self.cfg['ASR']['debug']:
          print 'ASR: speech_end()'
          sys.stdout.flush()

        hyp = self.asr.hyp_out()
        self.hypotheses_out.send(hyp)

      elif self.speech_start == "speech_start()":
        self.asr.rec_in(data_rec)

  def run(self):
    self.speech_start = False

    while 1:
      # process all pending commands
      if self.process_pending_commands():
        return

      # process audio data
      self.read_audio_write_asr_hypotheses()
