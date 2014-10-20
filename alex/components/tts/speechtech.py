#!/usr/bin/env python
# coding: utf-8

import urllib2
import socket
import json

import alex.utils.cache as cache
import alex.utils.audio as audio

from alex.components.tts import TTSInterface
from alex.components.tts.exceptions import TTSException
from alex.components.tts.preprocessing import TTSPreprocessing

class SpeechtechTTS(TTSInterface):
    """ Uses SpeechTech TTS service to synthesize sentences in a specific language, e.g. en, cs.

    The main function synthesize returns a string which contain a RIFF wave file audio of the synthesized text.

    """

    def __init__(self, cfg):
        super(SpeechtechTTS, self).__init__(cfg)
        self.preprocessing = TTSPreprocessing(self.cfg, self.cfg['TTS']['SpeechTech']['preprocessing'])

    @cache.lru_cache(10000)
    @cache.persistent_cache(True, 'SpeechtechTTS.get_tts_mp3.')
    def get_tts_mp3(self, voice, text):
        """ Access SpeechTech TTS service and get synthesized audio.

        Returns a string with wav in it.

        """

        try:
            TIMEOUT = 30
            LOGIN = self.cfg['TTS']['SpeechTech']['login']
            PASSWD = self.cfg['TTS']['SpeechTech']['password']
            ROOT_URI = 'http://services.speechtech.cz/tts/v3'

            if hasattr(socket, 'setdefaulttimeout'):
                socket.setdefaulttimeout(TIMEOUT)

            mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            mgr.add_password(None, ROOT_URI, LOGIN, PASSWD)
            auth = urllib2.HTTPDigestAuthHandler(mgr)
            opener = urllib2.build_opener(auth)

            mp3data = opener.open(ROOT_URI+'/synth', data=json.dumps({'text': text, 'engine': voice})).read()
            return mp3data

        except (urllib2.HTTPError, urllib2.URLError) as e:
            raise TTSException("SpeechTech TTS error: " + unicode(e))

        raise TTSException("Time out: No data synthesized.")

    def synthesize(self, text):
        """ Synthesize the text and returns it in a string with audio in default format and sample rate. """

        wav = b""
        
        try:
            if text:
                text = self.preprocessing.process(text)

                mp3 = self.get_tts_mp3(self.cfg['TTS']['SpeechTech']['voice'], text)
                wav = audio.convert_mp3_to_wav(self.cfg, mp3)
                wav = audio.change_tempo(self.cfg, self.cfg['TTS']['SpeechTech']['tempo'], wav)

#               if self.cfg['TTS']['debug']:
#                   m = "TTS cache hits %d and misses %d " % (self.get_tts_mp3.hits, self.get_tts_mp3.misses)
#                   self.cfg['Logging']['system_logger'].debug(m)
                return wav
            else:
                return b""
                
        except TTSException as e:
            m = unicode(e) + " Text: %s" % text
            self.cfg['Logging']['system_logger'].exception(m)
            return b""

        return wav
