#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import os.path
import struct
import wave
import sys
import math
import time

from datetime import datetime
from collections import deque

from SDS.components.hub.messages import Command, Frame

class VAD(multiprocessing.Process):
  """ VAD detects segments of speech in the audio stream.
  
  It process input signal and outputs only frames with speech. Every time a new speech segment starts, it sends
  'speech_start()' and everytime a speech segmends ends it sends 'speech_end()' commands.

  These commands has to be properly detected in the output stream by the following component.
  """

  def __init__(self, cfg, commands, audio_recorded_in, audio_played_in, audio_out):
    multiprocessing.Process.__init__(self)

    self.cfg = cfg
    self.commands = commands
    self.audio_recorded_in = audio_recorded_in
    self.audio_played_in = audio_played_in
    self.audio_out = audio_out

    self.output_file_name = None
    self.wf = None # wave file for logging

    if self.cfg['VAD']['type'] == 'power':
      self.in_frames = 1
      self.power_threshold_adapted = self.cfg['VAD']['power_threshold']

    # stores information about each frame whet it was speech or non speech
    self.speech_frames = [False, ]
    self.deque_audio_recorded_in = deque(maxlen=self.cfg['VAD']['power_decision_frames'])
    self.deque_audio_played_in = deque(maxlen=self.cfg['VAD']['power_decision_frames'])

    # keeps last decision about whether there is speech or non speech
    self.last_vad = False

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

      if isinstance(command, Command):
        if command.parsed['__name__'] == 'stop':
          # stop recording and playing
          if self.wf:
            self.wf.close()

          return True

        if command.parsed['__name__'] == 'flush':
          # discard all data in in input buffers
          while self.audio_recorded_in.poll():
            data_play = self.audio_recorded_in.recv()
          while self.audio_played_in.poll():
            data_play = self.audio_played_in.recv()

          self.deque_audio_recorded_in.clear()
          self.deque_audio_played_in.clear()
          
          return False

    return False

  def vad(self, data):
    speech_segment = False

    if self.cfg['VAD']['type'] == 'power':
      self.in_frames += 1

      a = struct.unpack('%dh'% (len(data)/2, ), data)
      a = [abs(x)**2 for x in a]
      energy = math.sqrt(sum(a))/len(a)

      if self.in_frames < self.cfg['VAD']['power_adaptation_frames']:
        self.power_threshold_adapted = self.in_frames*self.power_threshold_adapted
        self.power_threshold_adapted += energy
        self.power_threshold_adapted /= self.in_frames+1


      if energy > self.cfg['VAD']['power_threshold_multiplier']*self.power_threshold_adapted:
        speech_segment = 1.0

      self.speech_frames.append(speech_segment)

      detection_window = self.speech_frames[-self.cfg['VAD']['power_decision_frames']:]
      s = float(sum(detection_window))/len(detection_window)
      if self.cfg['VAD']['debug']:
        print 'E:', energy,
        print 'T:', self.power_threshold_adapted,
        print 'S:', s,

      vad = self.last_vad
      change = None
      if self.last_vad:
        # last decision was speech
        if s < self.cfg['VAD']['power_decision_non_speech_threshold']:
          vad = False
          change = 'non-speech'
      else:
        if s > self.cfg['VAD']['power_decision_speech_threshold']:
          vad = True
          change = 'speech'

      self.last_vad = vad

      return vad, change

    return False, None

  def read_write_audio(self):
    # read input audio
    while self.audio_recorded_in.poll():
      # read recorded audio
      data_rec = self.audio_recorded_in.recv()

      if isinstance(data_rec, Frame):
        # read played audio
        if self.audio_played_in.poll():
          data_played = self.audio_played_in.recv()
        else:
          data_played = Frame(b"\x00"*len(data_rec))

        # buffer the recorded and played audio
        self.deque_audio_recorded_in.append(data_rec)
        self.deque_audio_played_in.append(data_played)

        vad, change = self.vad(data_rec.payload)

        if self.cfg['VAD']['debug']:
          print vad, change,

        if change:
          if change == 'speech':
            # inform both the parent and the consumer
            self.audio_out.send(Command('speech_start()', 'VAD', 'AudioIn'))
            self.commands.send(Command('speech_start()', 'VAD', 'HUB'))
            # create new logging file
            self.output_file_name = os.path.join(self.cfg['Logging']['output_dir'],
                                                 'vad-'+datetime.now().isoformat('-').replace(':', '-')+'.wav')

            if self.cfg['VAD']['debug']:
              print self.output_file_name

            self.wf = wave.open(self.output_file_name, 'w')
            self.wf.setnchannels(2)
            self.wf.setsampwidth(2)
            self.wf.setframerate(self.cfg['Audio']['sample_rate'])

          if change == 'non-speech':
            # inform both the parent and the consumer
            self.audio_out.send(Command('speech_end()', 'VAD', 'AudioIn'))
            self.commands.send(Command('speech_end()', 'VAD', 'HUB'))
            # close the current logging file
            if self.wf:
              self.wf.close()

        if self.cfg['VAD']['debug']:
          if vad:
              print '+',
              sys.stdout.flush()
          else:
              print '-',
              sys.stdout.flush()

        if vad:
          while self.deque_audio_recorded_in:
            # send or save all potentially queued data
            # when there is change to speech there will be several frames of audio
            #   if there is no change then there will be only one queued frame

            data_rec = self.deque_audio_recorded_in.popleft()
            data_played = self.deque_audio_played_in.popleft()

            # send the result
            self.audio_out.send(data_rec)

            # save the recorded and played data
            data_stereo = bytearray()
            for i in range(self.cfg['Audio']['samples_per_frame']):
              data_stereo.extend(data_rec[i*2])
              data_stereo.extend(data_rec[i*2+1])
              # there might not be enough data to be played
              # then add zeros
              try:
                data_stereo.extend(data_played[i*2])
              except IndexError:
                data_stereo.extend(b'\x00')

              try:
                data_stereo.extend(data_played[i*2+1])
              except IndexError:
                data_stereo.extend(b'\x00')

            self.wf.writeframes(data_stereo)

  def run(self):
    while 1:
      time.sleep(self.cfg['Hub']['main_loop_sleep_time'])
      
      # process all pending commands
      if self.process_pending_commands():
        return

      # process audio data
      self.read_write_audio()




