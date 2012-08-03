#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys

import SDS.components.asr.google as GASR
import SDS.components.asr.julius as JASR

from SDS.components.hub.messages import Command, Frame, ASRHyp
from SDS.utils.exception import ASRException, JuliusASRException

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
    elif self.cfg['ASR']['type'] == 'Julius':
      self.asr = JASR.JuliusASR(cfg)
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

    if self.commands.poll():
      command = self.commands.recv()
      if self.cfg['ASR']['debug']:
        self.cfg['Logging']['system_logger'].debug(command)

      if isinstance(command, Command):
        if command.parsed['__name__'] == 'stop':
          return True

        if command.parsed['__name__'] == 'flush':
          # discard all data in in input buffers
          while self.audio_in.poll():
            data_in = self.audio_in.recv()

          self.asr.flush()

          return False

    return False

  def read_audio_write_asr_hypotheses(self):
    # read input audio
    while self.audio_in.poll():
      # read recorded audio
      data_rec = self.audio_in.recv()

      if isinstance(data_rec, Frame):
        if self.recognition_on:
          self.asr.rec_in(data_rec)
      elif isinstance(data_rec, Command):
        dr_speech_start = False

        if data_rec.parsed['__name__'] == "speech_start":
          dr_speech_start = "speech_start"
        elif data_rec.parsed['__name__'] == "speech_end":
          dr_speech_start = "speech_end"

        # check consistency of the input command
        if dr_speech_start:
          if self.recognition_on == False and dr_speech_start != "speech_start" and \
             self.recognition_on == True and dr_speech_start != "speech_end":
            raise ASRException('Commands received by the ASR component are inconsistent - recognition_on = %s - the new command: %s' % (self.recognition_on, dr_speech_start))

        if dr_speech_start == "speech_start":
          self.commands.send(Command("asr_start()", 'ASR', 'HUB'))
          self.recognition_on = True

          if self.cfg['ASR']['debug']:
            self.cfg['Logging']['system_logger'].debug('ASR: speech_start()')

        elif dr_speech_start == "speech_end":
          self.recognition_on = False

          if self.cfg['ASR']['debug']:
            self.cfg['Logging']['system_logger'].debug('ASR: speech_end()')

          try:
            hyp = self.asr.hyp_out()
          except JuliusASRException:
            hyp = None

          self.commands.send(Command("asr_end()", 'ASR', 'HUB'))
          self.hypotheses_out.send(ASRHyp(hyp))
      else:
        raise ASRException('Unsupported input.')

  def run(self):
    self.recognition_on = False

    while 1:
      time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

      # process all pending commands
      if self.process_pending_commands():
        return

      # process audio data
      self.read_audio_write_asr_hypotheses()
