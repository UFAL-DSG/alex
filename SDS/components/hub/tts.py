#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import sys

import SDS.components.tts.google as GTTS
import SDS.utils.various as various

from SDS.utils.exception import SDSException

class TTSException(SDSException):
  pass

class TTS(multiprocessing.Process):
  """ TTS synthesizes input text and returns speech audio signal.
  
  This component is a wrapper around multiple TTS engines which handles multiprocessing 
  communication.
  """

  def __init__(self, cfg, commands, text_in, audio_out):
    multiprocessing.Process.__init__(self)

    self.cfg = cfg
    self.commands = commands
    self.text_in = text_in
    self.audio_out = audio_out
    
    self.tts = None
    if self.cfg['TTS']['type'] == 'Google':
      self.tts = GTTS.GoogleTTS(cfg)
    else:
      raise TTSException('Unsupported TTS engine: %s' % (self.cfg['TTS']['type'], ))
    
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
        while self.text_in.poll():
          data_in = self.text_in.recv()

        return False

  def read_text_write_audio(self):
    # read input audio
    while self.text_in.poll():
      # read recorded audio
      text = self.text_in.recv()

      if self.cfg['TTS']['debug']:
        print 'TTS: Synthesize: ', text
        sys.stdout.flush()
        
      wav = self.tts.synthesize(text)
      wav = various.split_to_bins(wav, 2*self.cfg['AudioIO']['samples_per_buffer'])
      
      for frame in wav:
        self.audio_out.send(frame)
      
  def run(self):
    self.command = None
    while 1:
      # process all pending commands
      if self.process_pending_commands():
        return

      # process audio data
      self.read_text_write_audio()
