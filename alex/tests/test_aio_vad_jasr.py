#!/usr/bin/env python
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import autopath

import multiprocessing
import time

import alex.utils.audio as audio
import alex.utils.various as various

from alex.components.hub.aio import AudioIO
from alex.components.hub.vad import VAD
from alex.components.hub.asr import ASR
from alex.components.hub.messages import Command, Frame, ASRHyp

if __name__ == '__main__':

    cfg = {
        'Audio': {
        'sample_rate': 16000,
        'samples_per_frame': 160,
        },
        'AudioIO': {
        'debug': False,
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
        'ASR': {
        'debug': True,
        'type': 'Julius',
        'Julius': {
            'debug': False,
            'hostname': "localhost",
            'adinnetport': 5530,
            'serverport': 10500,
        }
        },
        'Hub': {
        'main_loop_sleep_time': 0.005,
        },
        'Logging': {
        'output_dir': './tmp'
        }
    }

    print "Test of the AudioIO, VAD and ASR components:"
    print "=" * 120

    wav = audio.load_wav(cfg, './resources/test16k-mono.wav')
    # split audio into frames
    wav = various.split_to_bins(wav, 2 * cfg['Audio']['samples_per_frame'])
    # remove the last frame

    aio_commands, aio_child_commands = multiprocessing.Pipe()  # used to send commands to AudioIO
    aio_record, aio_child_record = multiprocessing.Pipe()     # I read from this connection recorded audio
    aio_play, aio_child_play = multiprocessing.Pipe()         # I write in audio to be played

    vad_commands, vad_child_commands = multiprocessing.Pipe()  # used to send commands to VAD
    vad_audio_out, vad_child_audio_out = multiprocessing.Pipe()  # used to read output audio from VAD

    asr_commands, asr_child_commands = multiprocessing.Pipe()  # used to send commands to ASR
    asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe()  # used to read ASR hypotheses

    close_event = multiprocessing.Event()

    aio = AudioIO(cfg, aio_child_commands, aio_child_record, aio_child_play, close_event)
    vad = VAD(cfg, vad_child_commands, aio_record, vad_child_audio_out, close_event)
    asr = ASR(cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses, close_event)

    command_connections = [aio_commands, vad_commands, asr_commands]

    non_command_connections = [aio_record, aio_child_record,
                               aio_play, aio_child_play,
                               vad_audio_out, vad_child_audio_out,
                               asr_hypotheses_out, asr_child_hypotheses]

    aio.start()
    vad.start()
    asr.start()

    count = 0
    max_count = 5000
    while count < max_count:
        time.sleep(cfg['Hub']['main_loop_sleep_time'])
        count += 1

        # write one frame into the audio output
        if wav:
            data_play = wav.pop(0)
            #print len(wav), len(data_play)
            aio_play.send(Frame(data_play))

        # read all ASR output audio
        if asr_hypotheses_out.poll():
            asr_hyp = asr_hypotheses_out.recv()

            if isinstance(asr_hyp.hyp, ASRHyp):
                print asr_hyp.hyp

        # read all messages
        for c in command_connections:
            if c.poll():
                command = c.recv()
                print
                print command
                print

    # stop processes
    aio_commands.send(Command('stop()'))
    vad_commands.send(Command('stop()'))
    asr_commands.send(Command('stop()'))

    # clean connections
    for c in non_command_connections:
        while c.poll():
            c.recv()

    # wait for processes to stop
    aio.join()
    vad.join()
    asr.join()

    print
