#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

import argparse

import multiprocessing
import sys
import time

from alex.components.hub.vio import VoipIO
from alex.components.hub.vad import VAD
from alex.components.hub.messages import Command, Frame
from alex.utils.config import Config

#########################################################################
#########################################################################
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        test_vio_vad.py tests the VoipIO and VAD components.

        The program reads the default config in the resources directory ('../resources/default.cfg') and any
        additional config files passed as an argument of a '-c'. The additional config file
        overwrites any default or previous values.

      """)

    parser.add_argument('-c', "--configs", nargs='+',
                        help='additional configuration files')
    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)

    #########################################################################
    #########################################################################
    cfg['Logging']['system_logger'].info("Test of the VoipIO and VAD components\n" + "=" * 120)

    vio_commands, vio_child_commands = multiprocessing.Pipe()
    # used to send commands to VoipIO

    vio_record, vio_child_record = multiprocessing.Pipe()
    # I read from this connection recorded audio

    vio_play, vio_child_play = multiprocessing.Pipe()
    # I write in audio to be played


    vad_commands, vad_child_commands = multiprocessing.Pipe()
    # used to send commands to VAD

    vad_audio_out, vad_child_audio_out = multiprocessing.Pipe()
    # used to read output audio from VAD

    close_event = multiprocessing.Event()

    vio = VoipIO(cfg, vio_child_commands, vio_child_record, vio_child_play, close_event)
    vad = VAD(cfg, vad_child_commands, vio_record, vad_child_audio_out, close_event)

    command_connections = [vio_commands, vad_commands]

    non_command_connections = (vio_record, vio_child_record,
                               vio_play, vio_child_play,
                               vad_audio_out, vad_child_audio_out, )

    vio.start()
    vad.start()

    # Actively call a number configured.
    # vio_commands.send(Command('make_call(destination="sip:4366@SECRET:5066")', 'HUB', 'VoipIO'))

    count = 0
    max_count = 50000
    wav = None

    while count < max_count:
        time.sleep(cfg['Hub']['main_loop_sleep_time'])
        count += 1

        # write one frame into the audio output
        if wav:
            data_play = wav.pop(0)
            #print len(wav), len(data_play)
            vio_play.send(Frame(data_play))

        # read all VAD output audio
        if vad_audio_out.poll():
            data_vad = vad_audio_out.recv()

            if isinstance(data_vad, Command):
                if data_vad.parsed['__name__'] == 'speech_start':
                    print 'VAD:', 'Speech start'
                if data_vad.parsed['__name__'] == 'speech_end':
                    print 'VAD:', 'Speech end'

        # read all messages
        if vio_commands.poll():
            command = vio_commands.recv()

            if isinstance(command, Command):
                if command.parsed['__name__'] == "incoming_call" or command.parsed['__name__'] == "make_call":
                    wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
                    # split audio into frames
                    wav = various.split_to_bins(wav, 2 * cfg['Audio']['samples_per_frame'])

                    cfg['Logging']['system_logger'].session_start(command.parsed['remote_uri'])
                    cfg['Logging']['system_logger'].session_system_log('config = ' + unicode(cfg))
                    cfg['Logging']['system_logger'].info(command)

                    cfg['Logging']['session_logger'].session_start(cfg['Logging']['system_logger'].get_session_dir_name())
                    cfg['Logging']['session_logger'].config('config = ' + unicode(cfg))
                    cfg['Logging']['session_logger'].header(cfg['Logging']["system_name"], cfg['Logging']["version"])
                    cfg['Logging']['session_logger'].input_source("voip")

                elif command.parsed['__name__'] == "call_disconnected":
                    cfg['Logging']['system_logger'].info(command)

                    vio_commands.send(Command('flush()', 'HUB', 'VoipIO'))

                    cfg['Logging']['system_logger'].session_end()
                    cfg['Logging']['session_logger'].session_end()


        if vad_commands.poll():
            command = vad_commands.recv()
            cfg['Logging']['system_logger'].info(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == "speech_start":
                    u_voice_activity = True
                if command.parsed['__name__'] == "speech_end":
                    u_voice_activity = False
                    u_last_voice_activity_time = time.time()

        # read all messages
        for c in command_connections:
            if c.poll():
                command = c.recv()
                system_logger.info(command)

    # stop processes
    vio_commands.send(Command('stop()', 'HUB', 'VoipIO'))
    vad_commands.send(Command('stop()', 'HUB', 'VAD'))

    # clean connections
    for c in command_connections:
        while c.poll():
            c.recv()

    for c in non_command_connections:
        while c.poll():
            c.recv()

    # wait for processes to stop
    vio.join()
    system_logger.debug('VIO stopped.')
    vad.join()
    system_logger.debug('VAD stopped.')
