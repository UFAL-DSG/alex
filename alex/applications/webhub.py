#!/usr/bin/env python

import time
import multiprocessing
import argparse

if __name__ == "__main__":
    import autopath

from alex.components.hub import Hub
from alex.components.hub.webio import WebIO
from alex.components.hub.vad import VAD
from alex.components.hub.asr import ASR
from alex.components.hub.slu import SLU
from alex.components.hub.dm import DM
from alex.components.hub.nlg import NLG
from alex.components.hub.tts import TTS
from alex.components.hub.messages import Command
from alex.utils.config import Config


class WebHub(Hub):
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
        aio = WebIO(self.cfg, aio_child_commands, aio_child_record, aio_child_play, close_event)
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

        self.cfg['Logging']['system_logger'].session_start("@LOCAL_CALL")
        self.cfg['Logging']['system_logger'].session_system_log('config = ' + str(self.cfg))

        self.cfg['Logging']['session_logger'].session_start(
            self.cfg['Logging']['system_logger'].get_session_dir_name())
        self.cfg['Logging']['session_logger'].config('config = ' + str(self.cfg))
        self.cfg['Logging']['session_logger'].header(
            self.cfg['Logging']["system_name"], self.cfg['Logging']["version"])
        self.cfg['Logging']['session_logger'].input_source("aio")

        while 1:
            time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

            if call_back_time != -1 and call_back_time < time.time():
                aio_commands.send(Command('make_call(destination="%s")' %
                                          call_back_uri, 'HUB', 'AIO'))
                call_back_time = -1
                call_back_uri = None

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

            if slu_commands.poll():
                command = slu_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

            if dm_commands.poll():
                command = dm_commands.recv()
                self.cfg['Logging']['system_logger'].info(command)

                if isinstance(command, Command):
                    if command.parsed['__name__'] == "hangup":
                        # prepare for ending the call
                        pass

                    if command.parsed['__name__'] == "dm_da_generated":
                        # record the time of the last system generated dialogue act
                        pass

            if nlg_commands.poll():
                command = nlg_commands.recv()
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
        AudioHub runs the spoken dialog system, using your microphone and speakers.

        The default configuration is loaded from '<app root>/resources/default.cfg'.

        Additional configuration parameters can be passed as an argument '-c'.
        Any additional config parameters overwrite their previous values.
      """)

    parser.add_argument('-c', "--configs", nargs='+',
                        help='additional configuration files')
    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)

    cfg['Logging']['system_logger'].info("Webhub Hub\n" + "=" * 120)

    vhub = WebHub(cfg)
    vhub.run()


if __name__ == '__main__':
    main()
