#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['']

import sys
import os.path

# Add the directory containing the SDS package to python path
path, directory = os.path.split(os.path.abspath(__file__))
while directory and directory != 'SDS':
    path, directory = os.path.split(path)
if directory == 'SDS':
    sys.path.append(path)

class ASRInterface:
  """ This class basic interface which has to be provided by all ASR modules to fully function within
  the SDS project.
  """


  def rec_in(self, frame):
    """ This defines asynchronous interface for speech recognition.

    Call this input function with audio data belonging into one speech segment that should be
    recognized.

    Output hypotheses is obtained by calling hyp_out().
    """

    return

  def hyp_out(self):
    """ This defines asynchronous interface for speech recognition.

    Returns recognizers hypotheses about the input speech audio.
    """

    return

