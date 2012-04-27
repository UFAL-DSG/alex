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
