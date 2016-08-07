#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import argparse
import os

if __name__ == '__main__':
    import autopath

#from alex.applications.voicehub import VoiceHub
from voicehub import VoiceHub
from alex.components.hub import Hub
from alex.components.hub.vio import VoipIO
from alex.components.hub.vad import VAD
from alex.components.hub.asr import ASR
from alex.components.hub.slu import SLU
from alex.components.hub.dm import DM
from alex.components.hub.nlg import NLG
from alex.components.hub.tts import TTS
from alex.components.hub.messages import Command, DMDA
from alex.components.hub.calldb import CallDB
from alex.utils.config import Config


class VoipHub(VoiceHub):
    """
    VoipHub builds a full-featured VOIP telephone system.
    It builds a pipeline of ASR, SLU, DM, NLG, TTS components.
    Then it connects ASR and TTS with the VOIP to handle audio input and
    output.
    """

    voice_io_cls = VoipIO


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
        VoipHub builds a full featured VOIP telephone system.
        It builds a pipeline of VAD, ASR, SLU, DM, NLG, TTS components.
        Then it connects ASR and TTS with the VOIP to handle audio input and
        output.

        The program reads the default config in the resources directory
        ('../resources/default.cfg') config in the current directory.

        In addition, it reads all config file passed as an argument of a '-c'.
        The additional config files overwrites any default or previous values.

      """)

    parser.add_argument('-c', '--configs', nargs='+', help='additional configuration files')
    parser.add_argument('-n', '--ncalls', help='number of calls accepted before the hub automatically exits', type=int, default=0)

    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)

    cfg['Logging']['system_logger'].info("Voip Hub\n" + "=" * 120)

    vhub = VoipHub(cfg, args.ncalls)

    vhub.run()
