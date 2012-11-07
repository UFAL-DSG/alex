#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys
import random
import sys
import argparse

from __init__ import Hub

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.asr import ASR
from SDS.components.hub.dm import DM
from SDS.components.hub.nlg import NLG
from SDS.components.hub.tts import TTS
from SDS.components.hub.messages import Command
from SDS.utils.mproc import SystemLogger
from SDS.utils.config import Config

class VoipHub(Hub):
    """
      VoipHub builds a full featured VOIP telephone system.
      It builds a pipeline of ASR, SLU, DM, NLG, TTS components.
      Then it connects ASR and TTS with the VOIP to handle audio input and output.
    """
    def __init__(self, cfg):
        self.cfg = cfg

    def run(self):
        vio_commands, vio_child_commands = multiprocessing.Pipe()  # used to send commands to VoipIO
        vio_record, vio_child_record = multiprocessing.Pipe()      # I read from this connection recorded audio
        vio_play, vio_child_play = multiprocessing.Pipe()          # I write in audio to be played
        vio_played, vio_child_played = multiprocessing.Pipe()      # I read from this to get played audio
                                                                   #   which in sync with recorded signal

        vad_commands, vad_child_commands = multiprocessing.Pipe()   # used to send commands to VAD
        vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

        asr_commands, asr_child_commands = multiprocessing.Pipe()          # used to send commands to ASR
        asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe()  # used to read ASR hypotheses

        tts_commands, tts_child_commands = multiprocessing.Pipe()   # used to send commands to TTS
        tts_text_in, tts_child_text_in = multiprocessing.Pipe()     # used to send TTS text

        command_connections = [vio_commands, vad_commands, asr_commands, tts_commands]

        non_command_connections = [vio_record, vio_child_record,
                                   vio_play, vio_child_play,
                                   vio_played, vio_child_played,
                                   vad_audio_out, vad_child_audio_out,
                                   asr_hypotheses_out, asr_child_hypotheses,
#                                   dm_actions_out, asr_child_actions,
#                                   nlg_text_out, asr_child_text,
                                   tts_text_in, tts_child_text_in]

        vio = VoipIO(self.cfg, vio_child_commands, vio_child_record, vio_child_play, vio_child_played)
        vad = VAD(self.cfg, vad_child_commands, vio_record, vio_played, vad_child_audio_out)
        asr = ASR(self.cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses)
#        dm = DM(self.cfg, tts_child_commands, asr_hypotheses_out, asr_child_actions)
#        nlg = NLG(self.cfg, tts_child_commands, dm_actions_out, tts_child_text_in)
        tts = TTS(self.cfg, tts_child_commands, tts_text_in, vio_play)

        vio.start()
        vad.start()
        asr.start()
        #dm.start()
        #nlg.start()
        tts.start()

        # init the system
        call_start = 0
        s_voice_activity = False
        s_last_voice_activity_time = 0
        u_voice_activity = False
        u_last_voice_activity_time = 0

        while 1:
            time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

            if vad_audio_out.poll():
                data_vad = vad_audio_out.recv()

            if call_back_time != -1 and call_back_time < time.time():
                vio_commands.send(Command('make_call(destination="%s")' % call_back_uri, 'HUB', 'VoipIO'))
                call_back_time = -1
                call_back_uri = None

            # read all messages
            if vio_commands.poll():
                command = vio_commands.recv()

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "incoming_call":
                        self.cfg['Logging']['system_logger'].info(command)

                    if command.parsed['__name__'] == "rejected_call":
                        self.cfg['Logging']['system_logger'].info(command)

                        call_back_time = time.time() + self.cfg['VoipHub']['wait_time_before_calling_back']
                        call_back_uri = command.parsed['remote_uri']

                    if command.parsed['__name__'] == "rejected_call_from_blacklisted_uri":
                        self.cfg['Logging']['system_logger'].info(command)

                    if command.parsed['__name__'] == "call_connecting":
                        self.cfg['Logging']['system_logger'].info(command)

                    if command.parsed['__name__'] == "call_confirmed":
                        self.cfg['Logging']['system_logger'].info(command)

                        # init the system
                        call_start = time.time()

                        s_voice_activity = False
                        s_last_voice_activity_time = 0
                        u_voice_activity = False
                        u_last_voice_activity_time = 0

                    if command.parsed['__name__'] == "call_disconnected":
                        self.cfg['Logging']['system_logger'].info(command)
                        self.cfg['Logging']['system_logger'].call_end()

                        vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
                        vad_commands.send(Command('flush()', 'HUB', 'VAD'))
                        tts_commands.send(Command('flush()', 'HUB', 'TTS'))

                    if command.parsed['__name__'] == "play_utterance_start":
                        self.cfg['Logging']['system_logger'].info(command)
                        s_voice_activity = True

                    if command.parsed['__name__'] == "play_utterance_end":
                        self.cfg['Logging']['system_logger'].info(command)

                        s_voice_activity = False
                        s_last_voice_activity_time = time.time()

                        if command.parsed['user_id'] == last_intro_id:
                            intro_played = True
                            s_last_voice_activity_time = 0

            if vad_commands.poll():
                command = vad_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "speech_start":
                        u_voice_activity = True
                    if command.parsed['__name__'] == "speech_end":
                        u_voice_activity = False
                        u_last_voice_activity_time = time.time()

            if asr_commands.poll():
                command = asr_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

#            if dm_commands.poll():
#                command = dm_commands.recv()
#                self.cfg['Logging']['system_logger'].info(command)
#
#            if nlg_commands.poll():
#                command = nlg_commands.recv()
#                self.cfg['Logging']['system_logger'].info(command)
#
            if tts_commands.poll():
                command = tts_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

            # read the rest of messages
            for c in command_connections:
                if c.poll():
                    command = c.recv()
                    cfg['Logging']['system_logger'].info(command)

            current_time = time.time()
        # stop processes
        vio_commands.send(Command('stop()', 'HUB', 'VoipIO'))
        vad_commands.send(Command('stop()', 'HUB', 'VAD'))
        tts_commands.send(Command('stop()', 'HUB', 'TTS'))

        # clean connections
        for c in command_connections:
            while c.poll():
                c.recv()

        for c in non_command_connections:
            while c.poll():
                c.recv()

        # wait for processes to stop
        vio.join()
        vad.join()
        tts.join()

#########################################################################
#########################################################################

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        VoipHub builds a full featured VOIP telephone system.
        It builds a pipeline of ASR, SLU, DM, NLG, TTS components.
        Then it connects ASR and TTS with the VOIP to handle audio input and output.

        The program reads the default config in the resources directory ('../resources/default.cfg') config
        in the current directory.

        In addition, it reads all config file passed as an argument of a '-c'.
        The additional config files overwrites any default or previous values.

      """)

    parser.add_argument(
        '-c', action="store", dest="configs", default=None, nargs='+',
        help='additional configure file')
    args = parser.parse_args()

    cfg = Config('../../resources/default.cfg')

    if args.configs:
        for c in args.configs:
            cfg.merge(c)
    cfg['Logging']['system_logger'].info('config = ' + str(cfg))

    #########################################################################
    #########################################################################
    cfg['Logging']['system_logger'].info("Voip Hub\n" + "=" * 120)

    vhub = VoipHub(cfg)

    vhub.run()
