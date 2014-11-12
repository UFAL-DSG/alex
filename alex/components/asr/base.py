#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
from __future__ import unicode_literals

from alex.components.asr.exceptions import ASRException
from alex.utils.audio import load_wav
from alex.components.hub.messages import Frame


class ASRInterface(object):

    """
    This class basic interface which has to be provided by all ASR modules to
    fully function within the Alex project.

    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.syslog = cfg['Logging']['system_logger']

    def rec_in(self, frame):
        """
        This defines asynchronous interface for speech recognition.

        Call this input function with audio data belonging into one speech
        segment that should be recognized.

        Output hypothesis is obtained by calling hyp_out().

        """
        raise ASRException("Not implemented")

    def flush(self):
        """
        Should reset the decoder immediately in order to be ready for next recognition task

        """
        raise ASRException("Not implemented")

    def hyp_out(self):
        """
        This defines asynchronous interface for speech recognition.
        Returns recognizer's hypotheses about the input speech audio.

        """
        raise ASRException("Not implemented")

    def rec_wave(self, pcm):
        """Recognize whole pcm at once

        :pcm binary string representing 16bit, 16KHz wave

        """
        self.rec_in(pcm)
        return self.hyp_out()

    def rec_wav_file(self, wav_path):
        pcm = load_wav(self.cfg, wav_path)
        frame = Frame(pcm)
        res = self.rec_wave(frame)
        self.flush()
        return res
