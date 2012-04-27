#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
import urllib2

import SDS.utils.cache as cache
import SDS.utils.audio as audio

class GoogleTTS():
  """ Uses Google TTS service to synthesize sentences in a specific language, e.g. en, cs.

  The main function synthesize returns a string which contain a RIFF wave file audio of the synthesized text.

  """

  def __init__(self, cfg):
    self.cfg = cfg

  @cache.persistent_cache(True, 'GoogleTTS.get_tts_mp3.')
  def get_tts_mp3(self, language, text):
    """ Access Google TTS service and get synthesized audio.
    Note that the returned audio is in the MP3 format.

    Returns a string with MP3 in it.

    """

    baseurl  = "http://translate.google.com/translate_tts"
    values   = { 'q': text, 'tl': language }
    data     = urllib.urlencode(values)
    request  = urllib2.Request(baseurl, data)
    request.add_header("User-Agent", "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11" )
    mp3response = urllib2.urlopen(request)

    return mp3response.read()


  def synthesize(self, text):
    """ Synthesize the text and returns it in a string with audio in default format and sample rate. """

    mp3 = self.get_tts_mp3(self.cfg['TTS']['Google']['language'], text)
    wav = audio.convert_mp3_to_wav(self.cfg, mp3)

    return wav
    
