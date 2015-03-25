from unittest import TestCase

from alex.components.tts.voicerss import VoiceRssTTS
import alex.utils.audio as audio
import wave
from alex.utils.config import as_project_path

__author__ = 'm2rtin'


class TestVoiceRssTTS(TestCase):
    def test_synthesise_en(self):
        text = 'Hello, this is alex, the call is recorded, how may I help You?'
        cfg = {
            'Audio': {
                'sample_rate': 16000,
            },
            'TTS': {
                'type': 'VoiceRss',
                'VoiceRss': {
                    'language': 'en-us',
                    'preprocessing': as_project_path("resources/tts/prep_voicerss_en.cfg"),
                    'tempo': 1.0,
                    'api_key': 'ea29b823c83a426bbfe99f4cbce109f6'
                }
            }
        }
        wav_path = '/tmp/voice_rss_tts.wav'

        tts = VoiceRssTTS(cfg)
        wav = tts.synthesize(text)
        audio.save_wav(cfg, wav_path, wav)
        file = wave.open(wav_path)

        wav_length = float(file.getnframes()) / file.getframerate()
        self.assertEquals(5.292, wav_length)