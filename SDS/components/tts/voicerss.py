#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
import urllib2

import SDS.utils.cache as cache
import SDS.utils.audio as audio
from SDS.utils.exception import TTSException


class VoiceRssTTS():
    """\
    Uses The VoiceRSS TTS service to synthesize sentences in a
    specific language, e.g. en-us.

    The main function synthesize returns a string which contain a RIFF
    wave file audio of the synthesized text.
    """

    def __init__(self, cfg):
        """\
        Intitialize: just remember the configuration.
        """
        self.cfg = cfg

    @cache.persistent_cache(True, 'VoiceRssTTS.get_tts_wav.')
    def get_tts_wav(self, language, text):
        """\
        Access the VoiceRSS TTS service and get synthesized audio
        for a text.
        Returns a string with a WAV stream.
        """

        baseurl = "http://api.voicerss.org"
        values = {'src': text,
                  'hl': language,
                  'key': self.cfg['TTS']['VoiceRSS']['api_key']}
        data = urllib.urlencode(values)
        request = urllib2.Request(baseurl, data)
        request.add_header("User-Agent", "Mozilla/5.0 (X11; U; Linux i686) " +
                           "Gecko/20071127 Firefox/2.0.0.11")
        try:
            wavresponse = urllib2.urlopen(request)
            return audio.convert_wav(self.cfg, wavresponse.read())
        except Exception, e:
            raise TTSException("TTS error: " + str(e))

    def synthesize(self, text):
        """\
        Synthesize the text and return it in a string
        with audio in default format and sample rate.
        """

        wav = self.get_tts_wav(self.cfg['TTS']['VoiceRSS']['language'], text)
        return wav
