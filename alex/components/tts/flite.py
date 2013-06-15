#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tempfile import mkstemp
import subprocess

import alex.utils.cache as cache
import alex.utils.audio as audio

from alex.components.tts import TTSException, TTSInterface
from alex.components.tts.preprocessing import TTSPreprocessing


class FliteTTS(TTSInterface):
    """Uses Flite TTS to synthesize sentences in English.

    The main function `synthesize' returns a string which contains a RIFF wave
    file audio of the synthesized text.

    """

    def __init__(self, cfg):
        super(FliteTTS, self).__init__(cfg)
        self.preprocessing = TTSPreprocessing(self.cfg, self.cfg['TTS']['Flite']['preprocessing'])

    @cache.persistent_cache(True, 'FliteTTS.get_tts_wav.')
    def get_tts_wav(self, voice, text):
        """Runs flite from the command line and gets the synthesized audio.
        Note that the returned audio is in the re-sampled PCM audio format.

        """

        handle, wav_file_name = mkstemp('TmpSpeechFile.wav')

        if voice not in ['awb', 'rms', 'slt', 'kal', 'awb_time', 'kal16']:
            voice = 'awb'

        try:
            subprocess.call("flite -voice %s -t \"%s\" -o %s 2> /dev/null" %
                            (voice, text, wav_file_name), shell=True)
            wav = audio.load_wav(self.cfg, wav_file_name)
        except:
            raise TTSException("No data synthesized.")

        return wav

    def synthesize(self, text):
        """\
        Synthesizes the text and returns it as a string with audio in default
        format and sample rate.

        """

        try:
            text = self.preprocessing.process(text)
            
            wav = self.get_tts_wav(self.cfg['TTS']['Flite']['voice'], text)
        except TTSException:
            m = e + "Text: %" % text
            self.cfg['Logging']['system_logger'].warning(m)
            return b""

        return wav
