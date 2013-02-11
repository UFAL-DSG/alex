#!/usr/bin/env python
# -*- coding: utf-8 -*-

import __init__

import alex.utils.audio as audio

from alex.components.tts.google import GoogleTTS

if __name__ == '__main__':
    print "Testing Google TTS service"
    print "=" * 120
    print

    text = 'Dobrý den. Děkujeme za zavolání.'
    language = 'cs'
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
            'language': language
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
