#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
from alex.components.tts.voicerss import VoiceRssTTS

if __name__ == "__main__":
    import autopath

import alex.utils.audio as audio
from alex.utils.config import Config, as_project_path

if __name__ == '__main__':
    print "Testing VoiceRSS TTS"
    print "=" * 120
    print

    text = 'Hello, this is alex, the call is recorded, how may I help You?'
    voice = 'kal16'

    print "Synthesize text:", text
    print "Voice:          ", voice
    print

    c = {
          'TTS': {
        'debug': False,
        'type': 'VoiceRss',
         'VoiceRss': {
            'language': 'en-us',
            'preprocessing': as_project_path("resources/tts/prep_voicerss_en.cfg"),
            'tempo': 1.0,
            'api_key' : 'ea29b823c83a426bbfe99f4cbce109f6'
        }
    }
    }
    cfg = Config.load_configs(log=False)
    cfg.update(c)

    tts = VoiceRssTTS(cfg)

    print 'calling TTS'
    wav = tts.synthesize(text)

    print 'saving the TTS audio in ./tmp/voice_rss_tts.wav'
    audio.save_wav(cfg, './tmp/voice_rss_tts.wav', wav)

    print 'playing audio'
    audio.play(cfg, wav)
