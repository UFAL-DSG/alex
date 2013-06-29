#!/usr/bin/env python
# coding: utf-8


class TTSInterface(object):
    def __init__(self, cfg):
        self.cfg = cfg

    def synthesize(self, text):
        raise NotImplementedError("TTS")
