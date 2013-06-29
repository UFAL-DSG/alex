#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

if __name__ == "__main__":
    import autopath

import alex.utils.audio as audio

from alex.components.tts.flite import FliteTTS
from alex.utils.config import Config

if __name__ == '__main__':
    print "Testing Flite TTS"
    print "=" * 120
    print

    text = 'Hello. Thank you for calling. '
    voice = 'kal'

    print "Synthesize text:", text
    print "Voice:          ", voice
    print

    c = {
        'TTS': {
            'Flite': {
                'debug': False,
                'voice': 'kal'
            }
        }
    }
    cfg = Config.load_configs(log=False)
    cfg.update(c)

    tts = FliteTTS(cfg)

    print 'calling TTS'
    wav = tts.synthesize(text)

    print 'saving the TTS audio in ./tmp/flite_tts.wav'
    audio.save_wav(cfg, './tmp/flite_tts.wav', wav)

    print 'playing audio'
    audio.play(cfg, wav)
