#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import urllib
import urllib2

import alex.utils.cache as cache
import alex.utils.audio as audio

from alex.components.tts import TTSInterface
from alex.components.tts.exceptions import TTSException
from alex.components.tts.preprocessing import TTSPreprocessing


class GoogleTTS(TTSInterface):
    """
    Uses Google TTS service to synthesize sentences in a specific language,
    e.g. en, cs.

    The main function synthesize returns a string which contain a RIFF wave
    file audio of the synthesized text.

    """

    def __init__(self, cfg):
        super(GoogleTTS, self).__init__(cfg)
        self.preprocessing = TTSPreprocessing(
            self.cfg, self.cfg['TTS']['Google']['preprocessing'])

    @cache.persistent_cache(True, 'GoogleTTS.get_tts_mp3.')
    def get_tts_mp3(self, language, text, rate=1.0):
        """
        Access Google TTS service and get synthesized audio.
        Note that the returned audio is in the MP3 format.

        Returns a string with MP3 in it.

        """

        baseurl = "http://translate.google.com/translate_tts"
        values = {'q': text.encode('utf8'), 'tl': language, 'rate': rate}
        if self.cfg['TTS']['Google']['debug']:
            print values

        data = urllib.urlencode(values)
        request = urllib2.Request(baseurl, data)
        request.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.163 Safari/535.19")
        request.add_header('Referer', 'http://www.gstatic.com/translate/sound_player2.swf')

        mp3response = urllib2.urlopen(request)

        return mp3response.read()

    def synthesize(self, text):
        """
        Synthesize the text and returns it in a string with audio in default
        format and sample rate.
        """
        try:
            if text:
                text = self.preprocessing.process(text)

                mp3 = self.get_tts_mp3(self.cfg['TTS']['Google']['language'],
                                       text,
                                       self.cfg['TTS']['Google'].get('tempo', 1.0))
                wav = audio.convert_mp3_to_wav(self.cfg, mp3)
                wav = audio.change_tempo(self.cfg, self.cfg['TTS']['Google']['tempo'], wav)

                return wav
            else:
                return b""

        except TTSException as e:
            m = unicode(e) + " Text: %s" % text
            self.cfg['Logging']['system_logger'].exception(m)
            return b""
