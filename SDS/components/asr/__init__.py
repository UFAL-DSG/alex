#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__=['google',]

class ASRInterface:
  """ This class basic interface which has to be provided by all ASR modules to fully function within
  the SDS project.
  """

  def recognise(self, wav):
    """ Recognise the audio signal in the wav string.

    Returns a list of word hypotheses each with assigned probability confidence score.

    The probability scores must sum to one.
    """
    asrHyp = []
    #asrHyp = [0.X, "word string"]*N
    return asrHyp

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

