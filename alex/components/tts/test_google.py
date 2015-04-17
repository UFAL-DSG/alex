from unittest import TestCase

from alex.components.tts.google import GoogleTTS
import alex.utils.audio as audio
import wave
from alex.utils.config import as_project_path

__author__ = 'm2rtin'


class TestGoogleTTS(TestCase):
    def test_synthesise_en(self):
        text = 'Hello, this is Alex, How may i help You?'
        cfg = {
            'Audio': {
                'sample_rate': 16000,
            },
            'TTS': {
                'type': 'Google',
                'Google': {
                    'debug': True,
                    'language': 'en-us',
                    'preprocessing': as_project_path("resources/tts/prep_google_en.cfg"),
                    'tempo': 1.0,
                    },
                },
            }
        wav_path = '/tmp/google.wav'

        tts = GoogleTTS(cfg)
        wav = tts.synthesize(text)
        audio.save_wav(cfg, wav_path, wav)
        file = wave.open(wav_path)

        wav_length = float(file.getnframes()) / file.getframerate()
        self.assertGreaterEqual(3.5, wav_length)
        self.assertLessEqual(2.5, wav_length)