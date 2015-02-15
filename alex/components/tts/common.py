import inspect

import alex.components.tts.google as GTTS
import alex.components.tts.flite as FTTS
import alex.components.tts.speechtech as STTS
import alex.components.tts.voicerss as VTTS
from alex.components.tts import TTSInterface
from alex.components.tts.exceptions import TTSException


def get_tts_type(cfg):
    """Get TTS type from the configuration."""
    return cfg['TTS']['type']


def tts_factory(tts_type, cfg):
    if inspect.isclass(tts_type) and issubclass(tts_type, TTSInterface):
        slu = tts_type(cfg=cfg)
        return slu
    elif tts_type == 'Google':
        return GTTS.GoogleTTS(cfg)
    elif tts_type == 'Flite':
        return FTTS.FliteTTS(cfg)
    elif tts_type == 'SpeechTech':
        return STTS.SpeechtechTTS(cfg)
    elif tts_type == 'VoiceRss':
        return VTTS.VoiceRssTTS(cfg)
    else:
        raise TTSException('Unsupported TTS engine: %s' % (tts_type, ))
