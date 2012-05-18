#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os.path

__depth__ = 2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), *__depth__*[os.path.pardir])))

import SDS.utils.audio as audio

from SDS.components.asr.google import GoogleASR

print "Testing Google ASR service"
print "="*120
print
language = 'en'
sample_rate = 16000

print "Language:       ", language
print "Sample rate:    ", sample_rate
print

cfg = {
  'Audio': {
    'sample_rate': sample_rate
  },
  'ASR': {
    'Google': {
      'debug': False,
      'language' : language
    }
  }
}

asr = GoogleASR(cfg)

# testing audio
wav = audio.load_wav(cfg, './resources/test16k-mono.wav')

print 'playing audio'
audio.play(cfg, wav)

print 'calling ASR'
hyp = asr.recognize(wav)

print 'hypotheses'
print hyp


