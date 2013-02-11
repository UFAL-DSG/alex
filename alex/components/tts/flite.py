#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import remove
from tempfile import mkstemp
import subprocess

import alex.utils.cache as cache
import alex.utils.audio as audio

from alex.utils.exception import TTSException
from alex.utils.text import escape_special_characters_shell


class FliteTTS():
    """ Uses Flite TTS to synthesize sentences in a English language.

    The main function synthesize returns a string which contain a RIFF wave file audio of the synthesized text.

    """

    def __init__(self, cfg):
        self.cfg = cfg

    @cache.persistent_cache(True, 'FliteTTS.get_tts_wav.')
    def get_tts_wav(self, voice, text):
        """ Run flite from a command line and get synthesized audio.
        Note that the returned audio is in the resampled PCM audio format.

        """

        handle, wav_file_name = mkstemp('TmpSpeechFile.wav')

        if voice not in ['awb', 'rms', 'slt', 'kal', 'awb_time', 'kal16']:
            voice = 'awb'

        try:
            subprocess.call("flite -voice %s -t \"%s\" -o %s 2> /dev/null" %
                            (voice, text, wav_file_name), shell=True)
            wav = audio.load_wav(self.cfg, wav_file_name)
        except:
            raise TTSException("No data synthesised.")

        return wav

    def synthesize(self, text):
        """ Synthesize the text and returns it in a string with audio in default format and sample rate. """

        try:
            wav = self.get_tts_wav(self.cfg['TTS']['Flite']['voice'], text)
        except TTSException:
            # send empty wave data
            # FIXME: log the exception
            return ""

        return wav