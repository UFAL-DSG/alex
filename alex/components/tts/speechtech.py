#!/usr/bin/env python
# coding: utf-8

import sys
import urllib
import urllib2
import socket
import time
import random
import traceback

import alex.utils.cache as cache
import alex.utils.audio as audio

from alex.components.tts import TTSException, TTSInterface


class SpeechtechTTS(TTSInterface):
    """ Uses SpeechTech TTS service to synthesize sentences in a specific language, e.g. en, cs.

    The main function synthesize returns a string which contain a RIFF wave file audio of the synthesized text.

    """

    def __init__(self, cfg):
        self.cfg = cfg

    @cache.persistent_cache(True, 'SpeechtechTTS.get_tts_mp3.')
    def get_tts_mp3(self, voice, text):
        """ Access SpeechTech TTS service and get synthesized audio.

        Returns a string with wav in it.

        """

        try:
            TIMEOUT = 30
            LOGIN = self.cfg['TTS']['SpeechTech']['login']
            PASSWD = self.cfg['TTS']['SpeechTech']['password']
            REALM = 'TTS-Server'
            ROOT_URI = 'http://tts2.speechtech.cz'
            URI = '%s/add_to_queue' % ROOT_URI

            if hasattr(socket, 'setdefaulttimeout'):
                socket.setdefaulttimeout(TIMEOUT)

            # Create an OpenerDirector with support for Basic HTTP Authentication...
            auth_handler = urllib2.HTTPDigestAuthHandler()
            auth_handler.add_password(realm=REALM,
                                      uri=URI,
                                      user=LOGIN,
                                      passwd=PASSWD)
            opener = urllib2.build_opener(auth_handler)
            urllib2.install_opener(opener)

            params = urllib.urlencode([('text', text.encode('utf8')), ('engine', voice.encode('utf8'))])
            task_id = urllib2.urlopen(
                '%s/add_to_queue' % ROOT_URI, params).read().strip()

            uri = None
            i = 20
            while i:
                params = urllib.urlencode([('task_id', task_id)])
                resp = urllib2.urlopen(
                    '%s/query_status' % ROOT_URI, params).read().splitlines()
                code = int(resp[0])
                #print 'Status is', code
                if code == 3:
                    uri = resp[1]
                    #print 'Result available at', uri
                    break
                time.sleep(0.2)

                i -= 1

            if uri:
                request = urllib2.Request(uri)
                request.add_header("User-Agent", "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11")
                mp3response = urllib2.urlopen(request)

                return mp3response.read()
        except urllib2.HTTPError:
            raise TTSException("SpeechTech TTS error.")

        raise TTSException("Time out: No data synthesized.")

    def synthesize(self, text):
        """ Synthesize the text and returns it in a string with audio in default format and sample rate. """

        try:
            mp3 = self.get_tts_mp3(
                self.cfg['TTS']['SpeechTech']['voice'], text)
            wav = audio.convert_mp3_to_wav(self.cfg, mp3)

#            if self.cfg['TTS']['debug']:
#                m = "TTS cache hits %d and misses %d " % (self.get_tts_mp3.hits, self.get_tts_mp3.misses)
#                self.cfg['Logging']['system_logger'].debug(m)
            
        except TTSException as e:
            m = e + "Text: %" % text
            self.cfg['Logging']['system_logger'].warning(m)
            return b""

        return wav
