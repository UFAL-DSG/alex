from __future__ import unicode_literals

from alex.components.asr.exceptions import ASRException


def get_asr_type(cfg):
    """
    Reads the ASR type from the configuration.
    """
    return cfg['ASR']['type']


def asr_factory(cfg, asr_type=None):
    ''' Returns instance of specified ASR decoder in asr_type.

    The ASR decoders are imported on the fly,
    because they need external non Python libraries.
    '''
    if asr_type is None:
        asr_type = get_asr_type(cfg)
    t = get_asr_type(cfg)

    if t == 'Kaldi':
        from alex.components.asr.pykaldi import KaldiASR
        asr = KaldiASR(cfg)
    elif t == 'Google':
        from alex.components.asr.google import GoogleASR
        asr = GoogleASR(cfg)
    else:
        raise ASRException('Unsupported ASR decoder: %s' % asr_type)

    return asr
