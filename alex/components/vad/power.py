#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import math


class PowerVAD():
    """ This is implementation of a simple power based voice activity detector.

    It only implements simple decisions whether input frame is speech of non speech.
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.power_threshold_adapted = self.cfg['VAD']['power']['threshold']
        self.in_frames = 0

    def decide(self, frame):
        """Returns whether the input segment is speech or non speech.

        The returned values can be in range from 0.0 to 1.0.
        It returns 1.0 for 100% speech segment and 0.0 for 100% non speech segment.
        """

        speech_segment = 0.0

        self.in_frames += 1

        a = struct.unpack('%dh' % (len(frame) / 2, ), frame)
        a = [abs(x) ** 2 for x in a]
        energy = math.sqrt(sum(a)) / len(a)

        if self.in_frames < self.cfg['VAD']['power']['adaptation_frames']:
            self.power_threshold_adapted = self.in_frames * \
                self.power_threshold_adapted
            self.power_threshold_adapted += energy
            self.power_threshold_adapted /= self.in_frames + 1

        if energy > self.cfg['VAD']['power']['threshold_multiplier'] * self.power_threshold_adapted:
            speech_segment = 1.0

        return speech_segment
