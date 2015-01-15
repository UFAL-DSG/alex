#!/usr/bin/env python
# -*- coding: utf-8 -*-
if __name__  == '__main__':
    import autopath

import multiprocessing
import time

import alex.utils.audio as audio
import alex.utils.various as various

from alex.components.hub.aio import AudioIO
from alex.components.hub.vad import VAD
from alex.components.hub.messages import Command, Frame

if __name__  == '__main__':

    cfg = {
        'Audio': {
            'sample_rate': 16000
        },
        'AudioIO': {
        'debug': True,
        'samples_per_frame': 80,
        'play_buffer_size': 70,
        },
        'VAD': {
        'debug': False,
        'type': 'power',
        'power_threshold': 300,
        'power_threshold_multiplier': 1,
        'power_adaptation_frames': 20,
        'power_decision_frames': 25,
        'power_decision_speech_threshold': 0.7,
        'power_decision_non_speech_threshold': 0.2,
        },
        'Hub': {
        'main_loop_sleep_time': 0.005,
        },
        'Logging': {
        'output_dir': './tmp'
        }
    }

    print "Test of the AudioIO and VAD components:"
    print "=" * 120

    wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
    # split audio into frames
    wav = various.split_to_bins(wav, 2 * cfg['Audio']['samples_per_frame'])
    # remove the last frame

    aio_commands, aio_child_commands = multiprocessing.Pipe()  # used to send commands to AudioIO
    audio_record, child_audio_record = multiprocessing.Pipe()  # I read from this connection recorded audio
    audio_play, child_audio_play = multiprocessing.Pipe( )     # I write in audio to be played

    vad_commands, vad_child_commands = multiprocessing.Pipe()  # used to send commands to VAD
    vad_audio_out, vad_child_audio_out = multiprocessing.Pipe()# used to read output audio from VAD

    close_event = multiprocessing.Event()

    aio = AudioIO(cfg, aio_child_commands, child_audio_record, child_audio_play, close_event)
    vad = VAD(cfg, vad_child_commands, audio_record, vad_child_audio_out, close_event)

    command_connections = [aio_commands, vad_commands]

    aio.start()
    vad.start()

    count = 0
    max_count = 5000
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
                    print 'Speech start'
                if data_vad.parsed['__name__'] == 'speech_end':
                    print 'Speech end'

        # read all messages
        for c in command_connections:
            if c.poll():
                command = c.recv()
                print
                print command
                print

    aio_commands.send(Command('stop()'))
    vad_commands.send(Command('stop()'))
    aio.join()
    vad.join()

    print
