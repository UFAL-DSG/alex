#!/usr/bin/env python
# coding: utf-8

from alex.utils.exception import AlexException

class TTSException(AlexException):
    pass

class TTSInterface(object):
    def __init__(self, cfg):
        self.cfg = cfg
        
    def synthesize(self, text):
        raise NotImplementedError("TTS")
