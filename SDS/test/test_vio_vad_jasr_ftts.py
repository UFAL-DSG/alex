#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys
import argparse

import __init__

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.asr import ASR
from SDS.components.hub.tts import TTS
from SDS.components.hub.messages import Command, ASRHyp, TTSText
from SDS.utils.config import Config

#########################################################################
#########################################################################
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        test_vio_vad_jasr_ftts.py tests the VoipIO, VAD, ASR, and TTS
        components.

        This application uses the Julisu ASR and Flite TTS.

        The program reads the default config in the resources directory
        ('../resources/default.cfg') and any additional config files passed as
        an argument of a '-c'. The additional config file overwrites any
        default or previous values.

      """)

    parser.add_argument(
        '-c', action="store", dest="configs", default=None, nargs='+',
        help='additional configuration file')
    args = parser.parse_args()

    cfg = Config('../resources/default.cfg')
    if args.configs:
        for c in args.configs:
            cfg.merge(c)

    session_logger = cfg['Logging']['session_logger']
    system_logger = cfg['Logging']['system_logger']
    system_logger.info('config = {cfg!s}'.format(cfg=cfg))
    #########################################################################
    #########################################################################
    system_logger.info(
        "Test of the VoipIO, VAD, ASR, and TTS components\n" + "=" * 120)

    vio_commands, vio_child_commands = multiprocessing.Pipe()  # used to send commands to VoipIO
    vio_record, vio_child_record = multiprocessing.Pipe()     # I read from this connection recorded audio
    vio_play, vio_child_play = multiprocessing.Pipe()         # I write in audio to be played

    vad_commands, vad_child_commands = multiprocessing.Pipe()  # used to send commands to VAD
    vad_audio_out, vad_child_audio_out = multiprocessing.Pipe()  # used to read output audio from VAD

    asr_commands, asr_child_commands = multiprocessing.Pipe()  # used to send commands to ASR
    asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe()  # used to read ASR hypotheses

    tts_commands, tts_child_commands = multiprocessing.Pipe()  # used to send commands to TTS
    tts_text_in, tts_child_text_in = multiprocessing.Pipe()   # used to send TTS text

    command_connections = [vio_commands, vad_commands, asr_commands,
                           tts_commands]

    non_command_connections = [vio_record, vio_child_record,
                               vio_play, vio_child_play,
                               vad_audio_out, vad_child_audio_out,
                               asr_hypotheses_out, asr_child_hypotheses,
                               tts_text_in, tts_child_text_in]

    vio = VoipIO(cfg, vio_child_commands, vio_child_record, vio_child_play)
    vad = VAD(cfg, vad_child_commands, vio_record, vad_child_audio_out)
    asr = ASR(cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses)
    tts = TTS(cfg, tts_child_commands, tts_child_text_in, vio_play)

    vio.start()
    vad.start()
    asr.start()
    tts.start()

#     vio_commands.send(Command(
#         'make_call(destination="sip:{ext}@{dom}")'\
#             .format(ext=cfg['VoipIO']['extension'],
#                     dom=cfg['VoipIO']['domain']),
#         'HUB',
#         'VoipIO'))

    tts_text_in.send(TTSText(
        'Say something and the recognized text will be played back.'))

    count = 0
    max_count = 50000
    while count < max_count:
        time.sleep(cfg['Hub']['main_loop_sleep_time'])
        count += 1

        # read all messages
        if vio_commands.poll():
            command = vio_commands.recv()

            if isinstance(command, Command):
                if (command.parsed['__name__'] == "incoming_call"
                        or command.parsed['__name__'] == "make_call"):
                    system_logger.session_start(command.parsed['remote_uri'])
                    system_logger.session_system_log('config = ' + str(cfg))
                    system_logger.info(command)

                    session_logger.session_start(
                        system_logger.get_session_dir_name())
                    session_logger.config('config = {cfg!s}'.format(cfg=cfg))
                    session_logger.header(cfg['Logging']["system_name"],
                                          cfg['Logging']["version"])
                    session_logger.input_source("voip")

                if command.parsed['__name__'] == "rejected_call":
                    system_logger.info(command)

                if (command.parsed['__name__'] ==
                        "rejected_call_from_blacklisted_uri"):
                    system_logger.info(command)

                if command.parsed['__name__'] == "call_connecting":
                    system_logger.info(command)

                if command.parsed['__name__'] == "call_confirmed":
                    system_logger.info(command)

                if command.parsed['__name__'] == "call_disconnected":
                    system_logger.info(command)

                    system_logger.session_end()
                    session_logger.session_end()

        if asr_hypotheses_out.poll():
            asr_hyp = asr_hypotheses_out.recv()

            if isinstance(asr_hyp, ASRHyp):
                m = []
                m.append("Recognised hypotheses:")
                m.append("-" * 120)
                m.append(str(asr_hyp.hyp))
                system_logger.info('\n'.join(m))

                # get top hypotheses text
                top_text = asr_hyp.hyp.get_best_utterance()

                if top_text:
                    tts_text_in.send(TTSText('Recognized text: %s' % top_text))
                else:
                    tts_text_in.send(TTSText('Nothing was recognised'))

        # read all messages
        for c in command_connections:
            if c.poll():
                command = c.recv()
                system_logger.info(command)

    # stop processes
    vio_commands.send(Command('stop()'))
    vad_commands.send(Command('stop()'))
    asr_commands.send(Command('stop()'))
    tts_commands.send(Command('stop()'))

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
    asr.join()
    tts.join()
