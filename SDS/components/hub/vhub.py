#!/usr/bin/env python
# -*- coding: utf-8 -*-

from SDS.components.hub import Hub

class VoipHub(Hub):
    """
      VoipHub builds full featured VOIP telephone system.
      It builds a pipeline of ASR, SLU, DM, NLG, TTS components.
      Then it connects ASR and TTS with the VOIP to handle audio input and output.
    """
    def run(self):
        pass
