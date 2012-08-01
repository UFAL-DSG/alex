#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import struct
import time

from os import remove
from tempfile import mkstemp

class JuliusASR():
  """ Uses Julius ASR service to recognize recorded audio.

  The main function recognize returns a list of recognised hypotheses.
  One can also obtain a confusion network for the hypotheses.

  """

  def __init__(self, cfg):
    self.cfg = cfg
    self.hostname = self.cfg['ASR']['Julius']['hostname']
    self.serverport = self.cfg['ASR']['Julius']['serverport']
    self.adinnetport = self.cfg['ASR']['Julius']['adinnetport']

    self.connect_to_server()
    time.sleep(1)
    self.open_adinnet()

  def connect_to_server(self):
    """Connects to the Julius ASR server to start recognition and receive the recognition oputput."""

    self.s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.s_socket.connect((self.hostname, self.serverport))
    self.s_socket.setblocking(0)

  def open_adinnet(self):
    """Open the audio connection for sending the incoming frames."""

    self.a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.a_socket.connect((self.hostname, self.adinnetport))

  def send_frame(self, frame):
    """Sends one frame of audio data to the Julisus ASR"""

    self.a_socket.sendall(struct.pack("i", len(frame)))
    self.a_socket.sendall(frame)

  def audio_finished(self):
    """"Informs the Julius ASR about the end of segment and that the hypothesis should be finalised."""

    self.a_socket.sendall(struct.pack("i", 0))

  def read_audio_command(self):
    """Reads audio command from the Julius adinnet interface.

    Command:
      '0' - pause
      '1' - resume
      '2' - terminate
    """
    self.a_socket.setblocking(0)
    cmd = self.a_socket.recv(1)
    self.socket.a_setblocking(1)
    return cmd

  def read_server(self):
    """Reads messages from the Julius ASR server. """
    results = ""
    while True:
      try:
        results += self.s_socket.recv(1)
      except socket.error:
        pass

      if results and results[-1] == ".":
        break

    return results[-1].strip()

  def get_results(self):
    msg = ""

    while True:
      msg += self.read_server()+'\n'
      if '<INPUT STATUS="LISTEN"' in msg:
        return msg

  def flush(self):
    """Sends command to the Julius AST to terminate the recognition and get ready for new recognition

    FIX: not implemented
    """
    return

  def rec_in(self, frame):
    """ This defines asynchronous interface for speech recognition.

    Call this input function with audio data belonging into one speech segment that should be
    recognized.

    Output hypotheses is obtained by calling hyp_out().
    """

    self.send_frame(frame.payload)

    return

  def hyp_out(self):
    """ This defines asynchronous interface for speech recognition.

    Returns recognizers hypotheses about the input speech audio.
    """

    self.audio_finished()

    results = self.get_results()

    # process the results - generate the hypotheses

    return results
