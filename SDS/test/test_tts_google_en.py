#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __init__ import init_path

init_path()

import SDS.utils.audio as audio

from SDS.components.tts.google import GoogleTTS

print "Testing Google TTS service"
print "="*120
print

text = 'Hello. Thank you for calling.'
language = 'en'
sample_rate = 16000

print "Synthesize text:", text
print "Language:       ", language
print "Sample rate:    ", sample_rate
print

cfg = {
  'Audio': {
      'sample_rate': sample_rate
    },
  'TTS': {
    'Google': {
      'debug': False,
      'language' : language
    }
  }
}

tts = GoogleTTS(cfg)

print 'calling TTS'
wav = tts.synthesize(text)

print 'saving the TTS audio in ./tmp/google_tts.wav'
audio.save_wav(cfg, './tmp/google_tts.wav', wav)

print 'playing audio'
audio.play(cfg, wav)

