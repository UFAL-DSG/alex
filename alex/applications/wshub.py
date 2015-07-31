#!/usr/bin/env python

import time
import multiprocessing
import argparse

if __name__ == "__main__":
    import autopath

from alex.components.hub import Hub
from alex.components.hub.wsio import WSIO
from alex.components.hub.vad import VAD
from alex.components.hub.asr import ASR
from alex.components.hub.slu import SLU
from alex.components.hub.dm import DM, DMDA
from alex.components.hub.nlg import NLG
from alex.components.hub.tts import TTS
from alex.components.hub.messages import Command, ASRHyp, TTSText
from alex.utils.config import Config


class WSHub(Hub):
    def __init__(self, cfg):
        self.cfg = cfg

    def run(self):
        # AIO pipes
        # used to send commands to VoipIO
        aio_commands, aio_child_commands = multiprocessing.Pipe()
        # I read from this connection recorded audio
        aio_record, aio_child_record = multiprocessing.Pipe()
        # I write in audio to be played
        aio_play, aio_child_play = multiprocessing.Pipe()

        # VAD pipes
        # used to send commands to VAD
        vad_commands, vad_child_commands = multiprocessing.Pipe()
        # used to read output audio from VAD
        vad_audio_out, vad_child_audio_out = multiprocessing.Pipe()

        # ASR pipes
        # used to send commands to ASR
        asr_commands, asr_child_commands = multiprocessing.Pipe()
        # used to read ASR hypotheses
        asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe()

        # SLU pipes
        # used to send commands to SLU
        slu_commands, slu_child_commands = multiprocessing.Pipe()
        # used to read SLU hypotheses
        slu_hypotheses_out, slu_child_hypotheses = multiprocessing.Pipe()

        # DM pipes
        # used to send commands to DM
        dm_commands, dm_child_commands = multiprocessing.Pipe()
        # used to read DM actions
        dm_actions_out, dm_child_actions = multiprocessing.Pipe()

        # NLG pipes
        # used to send commands to NLG
        nlg_commands, nlg_child_commands = multiprocessing.Pipe()
        # used to read NLG output
        nlg_text_out, nlg_child_text = multiprocessing.Pipe()

        # TTS pipes
        # used to send commands to TTS
        tts_commands, tts_child_commands = multiprocessing.Pipe()

        command_connections = [aio_commands, vad_commands, asr_commands,
                               slu_commands, dm_commands, nlg_commands,
                               tts_commands]

        non_command_connections = [aio_record, aio_child_record,
                                   aio_play, aio_child_play,
                                   vad_audio_out, vad_child_audio_out,
                                   asr_hypotheses_out, asr_child_hypotheses,
                                   slu_hypotheses_out, slu_child_hypotheses,
                                   dm_actions_out, dm_child_actions,
                                   nlg_text_out, nlg_child_text]

        # create the hub components
        close_event = multiprocessing.Event()
        aio = WSIO(self.cfg, aio_child_commands, aio_child_record, aio_child_play, close_event)
        vad = VAD(self.cfg, vad_child_commands, aio_record, vad_child_audio_out, close_event)
        asr = ASR(self.cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses, close_event)
        slu = SLU(
            self.cfg, slu_child_commands, asr_hypotheses_out, slu_child_hypotheses, close_event)
        dm = DM(self.cfg, dm_child_commands, slu_hypotheses_out, dm_child_actions, close_event)
        nlg = NLG(self.cfg, nlg_child_commands, dm_actions_out, nlg_child_text, close_event)
        tts = TTS(self.cfg, tts_child_commands, nlg_text_out, aio_play, close_event)

        # start the hub components
        aio.start()
        vad.start()
        asr.start()
        slu.start()
        dm.start()
        nlg.start()
        tts.start()

        # init the system
        call_back_time = -1
        call_back_uri = None
        call_start = time.time()

        self.cfg['Logging']['session_logger'].set_close_event(close_event)
        self.cfg['Logging']['session_logger'].set_cfg(self.cfg)
        self.cfg['Logging']['session_logger'].start()

        self.cfg['Logging']['system_logger'].session_start("LOCAL_CALL")
        self.cfg['Logging']['system_logger'].session_system_log('config = ' + str(self.cfg))

        self.cfg['Logging']['session_logger'].session_start(
            self.cfg['Logging']['system_logger'].get_session_dir_name())
        self.cfg['Logging']['session_logger'].config('config = ' + str(self.cfg))
        self.cfg['Logging']['session_logger'].header(
            self.cfg['Logging']["system_name"], self.cfg['Logging']["version"])
        self.cfg['Logging']['session_logger'].input_source("aio")



        while 1:
            time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

            # read all messages
            if aio_commands.poll():
                command = aio_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "client_connected":
                        dm_commands.send(Command('new_dialogue()', 'HUB', 'DM'))
                        vad_commands.send(Command('flush()', 'HUB', 'VAD '))


            if vad_commands.poll():
                command = vad_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "speech_start":
                        pass
                    if command.parsed['__name__'] == "speech_end":
                        pass

            if asr_commands.poll():
                command = asr_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

                if isinstance(command, ASRHyp):
                    aio_commands.send(command)

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
                        self.cfg['Analytics'].track_event('vhub', 'system_hangup')

                    if command.parsed['__name__'] == "flushed":
                        # flush nlg, when flushed, tts will be flushed
                        nlg_commands.send(Command('flush()', 'HUB', 'NLG'))

                elif isinstance(command, DMDA):
                    # record the time of the last system generated dialogue act
                    s_last_dm_activity_time = time.time()

                    if command.da != "silence()":
                        # if the DM generated non-silence dialogue act, then continue in processing it
                        nlg_commands.send(DMDA(command.da, "HUB", "NLG"))

            if nlg_commands.poll():
                command = nlg_commands.recv()

                if isinstance(command, TTSText):
                    aio_commands.send(command)

                # TODO HACK
                # self.cfg['Logging']['system_logger'].info(command)

            if tts_commands.poll():
                command = tts_commands.recv()
                # TODO HACK
                # self.cfg['Logging']['system_logger'].info(command)

            current_time = time.time()

        # stop processes
        aio_commands.send(Command('stop()', 'HUB', 'AIO'))
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
        aio.join()
        vad.join()
        tts.join()


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
      """)

    parser.add_argument('-c', "--configs", nargs='+',
                        help='additional configuration files')
    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)

    cfg['Logging']['system_logger'].info("WSHub Hub\n" + "=" * 120)

    vhub = WSHub(cfg)
    vhub.run()


if __name__ == '__main__':
    main()
