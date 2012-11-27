#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys
import argparse

import __init__

import SDS.utils.audio as audio
import SDS.utils.various as various

from SDS.components.hub.vio import VoipIO
from SDS.components.hub.vad import VAD
from SDS.components.hub.messages import Command, Frame
from SDS.utils.config import Config

#########################################################################
#########################################################################
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        test_vio_vad_jasr_ftts.py tests the VoipIO, VAD, ASR, and TTS components.

        This application uses the Julisu ASR and Flite TTS.

        The program reads the default config in the resources directory ('../resources/default.cfg') and any
        additional config files passed as an argument of a '-c'. The additional config file
        overwrites any default or previous values.

      """)

    parser.add_argument(
        '-c', action="store", dest="configs", default=None, nargs='+',
        help='additional configure file')
    args = parser.parse_args()

    cfg = Config('../resources/default.cfg')
    if args.configs:
        for c in args.configs:
            cfg.merge(c)
    cfg['Logging']['system_logger'].info('config = ' + str(cfg))

    #########################################################################
    #########################################################################
    cfg['Logging']['system_logger'].info(
        "Test of the VoipIO and VAD components\n" + "=" * 120)

    wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
    # split audio into frames
    wav = various.split_to_bins(wav, 2 * cfg['Audio']['samples_per_frame'])
    # remove the last frame

    vio_commands, vio_child_commands = multiprocessing.Pipe()  # used to send vio_commands
    audio_record, child_audio_record = multiprocessing.Pipe()  # I read from this connection recorded audio
    audio_play, child_audio_play = multiprocessing.Pipe()     # I write in audio to be played

    vad_commands, vad_child_commands = multiprocessing.Pipe()  # used to send commands to VAD
    vad_audio_out, vad_child_audio_out = multiprocessing.Pipe()  # used to read output audio from VAD

    vio = VoipIO(cfg, vio_child_commands, child_audio_record,child_audio_play)
    vad = VAD(cfg, vad_child_commands, audio_record, vad_child_audio_out)

    command_connections = [vio_commands, vad_commands]

    vio.start()
    vad.start()

    vio_commands.send(Command('make_call(destination="sip:4366@SECRET:5066")', 'HUB', 'VoipIO'))

    count = 0
    max_count = 50000
    while count < max_count:
        time.sleep(cfg['Hub']['main_loop_sleep_time'])
        count += 1

        # write one frame into the audio output
        if wav:
            data_play = wav.pop(0)
            #print len(wav), len(data_play)
            audio_play.send(Frame(data_play))

        # read all VAD output audio
        if vad_audio_out.poll():
            data_vad = vad_audio_out.recv()

            if isinstance(data_vad, Command):
                if data_vad.parsed['__name__'] == 'speech_start':
                    print 'VAD:', 'Speech start'
                if data_vad.parsed['__name__'] == 'speech_end':
                    print 'VAD:', 'Speech end'

        # read all messages
        for c in command_connections:
            if c.poll():
                command = c.recv()
                print
                print command
                print

        sys.stdout.flush()

    vio_commands.send(Command('stop()'))
    vad_commands.send(Command('stop()'))
    vio.join()
    vad.join()

    print
