#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

import autopath

class ASRInterface(object):
    """
    This class basic interface which has to be provided by all ASR modules to
    fully function within the Alex project.

    """

    def rec_in(self, frame):
        """
        This defines asynchronous interface for speech recognition.

        Call this input function with audio data belonging into one speech
        segment that should be recognized.

        Output hypothesis is obtained by calling hyp_out().

        """
        return

    def hyp_out(self):
        """
        This defines asynchronous interface for speech recognition.

        Returns recognizer's hypotheses about the input speech audio.

        """
        return
