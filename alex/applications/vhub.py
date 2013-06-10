#!/usr/bin/env python
# -*- coding: utf-8 -*-
import autopath

import multiprocessing
import time
import sys
import random
import sys
import argparse

from alex.components.hub import Hub
from alex.components.hub.vio import VoipIO
from alex.components.hub.vad import VAD
from alex.components.hub.asr import ASR
from alex.components.hub.slu import SLU
from alex.components.hub.dm import DM
from alex.components.hub.nlg import NLG
from alex.components.hub.tts import TTS
from alex.components.hub.messages import Command
from alex.utils.config import Config


class VoipHub(Hub):
    """\
    VoipHub builds a full-featured VOIP telephone system.
    It builds a pipeline of ASR, SLU, DM, NLG, TTS components.
    Then it connects ASR and TTS with the VOIP to handle audio input and
    output.
    """

    def __init__(self, cfg):
        self.cfg = cfg

    def run(self):
        vio_commands, vio_child_commands = multiprocessing.Pipe()  # used to send commands to VoipIO
        vio_record, vio_child_record = multiprocessing.Pipe()      # I read from this connection recorded audio
        vio_play, vio_child_play = multiprocessing.Pipe()          # I write in audio to be played

        vad_commands, vad_child_commands = multiprocessing.Pipe()   # used to send commands to VAD
        vad_audio_out, vad_child_audio_out = multiprocessing.Pipe() # used to read output audio from VAD

        asr_commands, asr_child_commands = multiprocessing.Pipe()          # used to send commands to ASR
        asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe()  # used to read ASR hypotheses

        slu_commands, slu_child_commands = multiprocessing.Pipe()          # used to send commands to SLU
        slu_hypotheses_out, slu_child_hypotheses = multiprocessing.Pipe()  # used to read SLU hypotheses

        dm_commands, dm_child_commands = multiprocessing.Pipe()            # used to send commands to DM
        dm_actions_out, dm_child_actions = multiprocessing.Pipe()          # used to read DM actions

        nlg_commands, nlg_child_commands = multiprocessing.Pipe()          # used to send commands to NLG
        nlg_text_out, nlg_child_text = multiprocessing.Pipe()              # used to read NLG output

        tts_commands, tts_child_commands = multiprocessing.Pipe()          # used to send commands to TTS

        command_connections = [vio_commands, vad_commands, asr_commands, slu_commands,
                                             dm_commands, nlg_commands, tts_commands]

        non_command_connections = [vio_record, vio_child_record,
                                   vio_play, vio_child_play,
                                   vad_audio_out, vad_child_audio_out,
                                   asr_hypotheses_out, asr_child_hypotheses,
                                   slu_hypotheses_out, slu_child_hypotheses,
                                   dm_actions_out, dm_child_actions,
                                   nlg_text_out, nlg_child_text]

        vio = VoipIO(self.cfg, vio_child_commands, vio_child_record, vio_child_play)
        vad = VAD(self.cfg, vad_child_commands, vio_record, vad_child_audio_out)
        asr = ASR(self.cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses)
        slu = SLU(self.cfg, slu_child_commands, asr_hypotheses_out, slu_child_hypotheses)
        dm  =  DM(self.cfg,  dm_child_commands, slu_hypotheses_out, dm_child_actions)
        nlg = NLG(self.cfg, nlg_child_commands, dm_actions_out, nlg_child_text)
        tts = TTS(self.cfg, tts_child_commands, nlg_text_out, vio_play)

        vio.start()
        vad.start()
        asr.start()
        slu.start()
        dm.start()
        nlg.start()
        tts.start()

        # init the system
        call_start = 0
        call_back_time = -1
        call_back_uri = None
        number_of_turns = -1

        s_voice_activity = False
        s_last_voice_activity_time = 0
        u_voice_activity = False
        u_last_voice_activity_time = 0

        s_last_dm_activity_time = 0

        hangup = False

        while 1:
            time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

            if call_back_time != -1 and call_back_time < time.time():
                vio_commands.send(Command('make_call(destination="%s")' % call_back_uri, 'HUB', 'VoipIO'))
                call_back_time = -1
                call_back_uri = None

            # read all messages
            if vio_commands.poll():
                command = vio_commands.recv()

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "incoming_call":
                        self.cfg['Logging']['system_logger'].session_start(command.parsed['remote_uri'])
                        self.cfg['Logging']['system_logger'].session_system_log('config = ' + str(self.cfg))
                        self.cfg['Logging']['system_logger'].info(command)

                        self.cfg['Logging']['session_logger'].session_start(self.cfg['Logging']['system_logger'].get_session_dir_name())
                        self.cfg['Logging']['session_logger'].config('config = ' + str(self.cfg))
                        self.cfg['Logging']['session_logger'].header(self.cfg['Logging']["system_name"], self.cfg['Logging']["version"])
                        self.cfg['Logging']['session_logger'].input_source("voip")

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
                        number_of_turns = 0

                        s_voice_activity = False
                        s_last_voice_activity_time = 0
                        u_voice_activity = False
                        u_last_voice_activity_time = 0
                        hungup = False

                        dm_commands.send(Command('new_dialogue()', 'HUB', 'DM'))

                    if command.parsed['__name__'] == "call_disconnected":
                        self.cfg['Logging']['system_logger'].info(command)

                        vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))
                        vad_commands.send(Command('flush()', 'HUB', 'VAD'))
                        asr_commands.send(Command('flush()', 'HUB', 'ASR'))
                        slu_commands.send(Command('flush()', 'HUB', 'SLU'))
                        dm_commands.send(Command('flush()', 'HUB', 'DM'))
                        nlg_commands.send(Command('flush()', 'HUB', 'NLG'))
                        tts_commands.send(Command('flush()', 'HUB', 'TTS'))

                        dm_commands.send(Command('end_dialogue()', 'HUB', 'DM'))

                        # FIXME: this is not an ideal synchronisation for the stopped components
                        # we should do better.
                        # FJ
                        time.sleep(0.5)

                        self.cfg['Logging']['system_logger'].session_end()
                        self.cfg['Logging']['session_logger'].session_end()

                    if command.parsed['__name__'] == "play_utterance_start":
                        self.cfg['Logging']['system_logger'].info(command)
                        s_voice_activity = True
                        s_last_voice_activity_time = time.time()

                    if command.parsed['__name__'] == "play_utterance_end":
                        self.cfg['Logging']['system_logger'].info(command)

                        s_voice_activity = False
                        s_last_voice_activity_time = time.time()

            if vad_commands.poll():
                command = vad_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "speech_start":
                        u_voice_activity = True

                        if s_voice_activity:
                            self.cfg['Logging']['session_logger'].barge_in("system")

                    if command.parsed['__name__'] == "speech_end":
                        u_voice_activity = False
                        u_last_voice_activity_time = time.time()

            if asr_commands.poll():
                command = asr_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

            if slu_commands.poll():
                command = slu_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

            if dm_commands.poll():
                command = dm_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "hangup":
                        # prepare for ending the call
                        hangup = True

                    if command.parsed['__name__'] == "dm_da_generated":
                        # record the time of the last system generated dialogue act
                        s_last_dm_activity_time = time.time()
                        number_of_turns += 1

                        tts_commands.send(Command('keeplast()', 'HUB', 'TTS'))

                    # if a dialogue act is generated, stop playing current TTS audio
                    if not hangup and command.parsed['__name__'] == "dm_da_generated":
                        vio_commands.send(Command('flush_out()', 'HUB', 'VIO'))
                        s_voice_activity = False
                        s_last_voice_activity_time = time.time()

            if nlg_commands.poll():
                command = nlg_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

            if tts_commands.poll():
                command = tts_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

            current_time = time.time()

            if hangup and s_last_dm_activity_time + 2.0 < current_time and \
                s_voice_activity == False and s_last_voice_activity_time + 2.0 < current_time:
                # we are ready to hangup only when all voice activity finished,
                hangup = False
                vio_commands.send(Command('hangup()', 'HUB', 'VoipIO'))

            # hard hangup due to the hard limits
            if number_of_turns != -1 and current_time - call_start > self.cfg['VoipHub']['hard_time_limit'] or \
                number_of_turns > self.cfg['VoipHub']['hard_turn_limit']:
                number_of_turns = -1
                vio_commands.send(Command('hangup()', 'HUB', 'VoipIO'))


        # stop processes
        vio_commands.send(Command('stop()', 'HUB', 'VoipIO'))
        vad_commands.send(Command('stop()', 'HUB', 'VAD'))
        asr_commands.send(Command('stop()', 'HUB', 'ASR'))
        slu_commands.send(Command('stop()', 'HUB', 'SLU'))
        dm_commands.send(Command('stop()', 'HUB', 'DM'))
        nlg_commands.send(Command('stop()', 'HUB', 'NLG'))
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

    parser.add_argument(
        '-c', action="append", dest="configs", default=None,
        help='additional configure file')
    args = parser.parse_args()

    cfg = Config('resources/default.cfg', True)

    if args.configs:
        for c in args.configs:
            cfg.merge(c)
    cfg['Logging']['system_logger'].info('config = ' + str(cfg))

    #########################################################################
    #########################################################################
    cfg['Logging']['system_logger'].info("Voip Hub\n" + "=" * 120)

    vhub = VoipHub(cfg)

    vhub.run()
