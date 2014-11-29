#!/usr/bin/env python
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import autopath

import multiprocessing
import time

from alex.components.hub.aio import AudioIO
from alex.components.hub.vad import VAD
from alex.components.hub.asr import ASR
from alex.components.hub.tts import TTS
from alex.components.hub.messages import Command, ASRHyp, TTSText

if __name__ == '__main__':

    cfg = {
        'Audio': {
        'sample_rate': 16000,
        'samples_per_frame': 80,
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
        'type': 'Google',
        'Google': {
            'debug': False,
            'language': 'en'
        }
        },
        'TTS': {
        'debug': True,
        'type': 'Google',
        'Google': {
            'debug': False,
            'language': 'en'
        }
        },
        'Hub': {
        'main_loop_sleep_time': 0.005,
        },
        'Logging': {
        'output_dir': './tmp'
        }
    }

    print "Test of the AudioIO, VAD, ASR and TTS components:"
    print "=" * 120

    aio_commands, aio_child_commands = multiprocessing.Pipe()  # used to send commands to AudioIO
    aio_record, aio_child_record = multiprocessing.Pipe()     # I read from this connection recorded audio
    aio_play, aio_child_play = multiprocessing.Pipe()         # I write in audio to be played

    vad_commands, vad_child_commands = multiprocessing.Pipe()  # used to send commands to VAD
    vad_audio_out, vad_child_audio_out = multiprocessing.Pipe()  # used to read output audio from VAD

    asr_commands, asr_child_commands = multiprocessing.Pipe()  # used to send commands to ASR
    asr_hypotheses_out, asr_child_hypotheses = multiprocessing.Pipe()  # used to read ASR hypotheses

    tts_commands, tts_child_commands = multiprocessing.Pipe()  # used to send commands to TTS
    tts_text_in, tts_child_text_in = multiprocessing.Pipe()   # used to send TTS text

    command_connections = [aio_commands, vad_commands, asr_commands, tts_commands]

    non_command_connections = [aio_record, aio_child_record,
                               aio_play, aio_child_play,
                               vad_audio_out, vad_child_audio_out,
                               asr_hypotheses_out, asr_child_hypotheses,
                               tts_text_in, tts_child_text_in]

    close_event = multiprocessing.Event()

    aio = AudioIO(cfg, aio_child_commands, aio_child_record, aio_child_play, close_event)
    vad = VAD(cfg, vad_child_commands, aio_record, vad_child_audio_out, close_event)
    asr = ASR(cfg, asr_child_commands, vad_audio_out, asr_child_hypotheses, close_event)
    tts = TTS(cfg, tts_child_commands, tts_child_text_in, aio_play, close_event)

    aio.start()
    vad.start()
    asr.start()
    tts.start()

    tts_text_in.send(
        TTSText('Say something and the recognized text will be played back.'))

    count = 0
    max_count = 15000
    while count < max_count:
        time.sleep(cfg['Hub']['main_loop_sleep_time'])
        count += 1

        if asr_hypotheses_out.poll():
            asr_hyp = asr_hypotheses_out.recv()

            if isinstance(asr_hyp, ASRHyp):
                if len(asr_hyp.hyp):
                    print asr_hyp.hyp

                    # get top hypotheses text
                    top_text = asr_hyp.hyp[0][1]

                    tts_text_in.send(TTSText('Recognized text: ' + top_text))
                else:
                    # nothing was recognised
                    print 'Nothing was recognised.'

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
    tts_commands.send(Command('stop()'))

    # clean connections
    for c in non_command_connections:
        while c.poll():
            c.recv()

    # wait for processes to stop
    aio.join()
    vad.join()
    asr.join()
    tts.join()

    print
