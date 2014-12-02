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
from alex.components.hub.messages import Command, Frame
from alex.utils.config import Config

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        test_vio.py tests the VoipIO component.

        The program reads the default config in the resources directory
        ('../resources/default.cfg') and any additional config files passed as
        an argument of a '-c'. The additional config file overwrites any
        default or previous values.

      """)

    parser.add_argument('-c', "--configs", nargs='+',
                        help='additional configuration files')
    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)

    session_logger = cfg['Logging']['session_logger']
    system_logger = cfg['Logging']['system_logger']

    #########################################################################
    #########################################################################
    system_logger.info("Test of the VoipIO component\n" + "=" * 120)

    vio_commands, vio_child_commands = multiprocessing.Pipe()
    # used to send commands to VoipIO

    vio_record, vio_child_record = multiprocessing.Pipe()
    # I read from this connection recorded audio

    vio_play, vio_child_play = multiprocessing.Pipe()
    # I write in audio to be played

    command_connections = (vio_commands, )

    non_command_connections = (vio_record, vio_child_record,
                               vio_play, vio_child_play, )

    close_event = multiprocessing.Event()

    vio = VoipIO(cfg, vio_child_commands, vio_child_record, vio_child_play, close_event)

    vio.start()

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

        # read all recorded audio
        if vio_record.poll():
            data_rec = vio_record.recv()

        # read all messages from VoipIO
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

        # read all messages
        for c in command_connections:
            if c.poll():
                command = c.recv()
                system_logger.info(command)

    # stop processes
    vio_commands.send(Command('stop()', 'HUB', 'VoipIO'))

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
