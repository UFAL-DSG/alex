#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import os.path
import wave
import sys
import time

from datetime import datetime
from collections import deque

from SDS.utils.exception import ASRException

import SDS.components.vad.power as PVAD
import SDS.components.vad.gmm as GVAD

from SDS.components.hub.messages import Command, Frame


class VAD(multiprocessing.Process):
    """ VAD detects segments of speech in the audio stream.

    It implements two smoothing windows, one for detection speech and one for detection of silence.
    1) The speech window is typically shorter so that the detection if more responsive towards the speech,
       it is easy to activate for the speech.
    2) The silence windows should be longer so that short pauses are not triggered and only one speech segment
       including the short pauses is generated.

    It process input signal and outputs only frames with speech. Every time a new speech segment starts, it sends
    'speech_start()' and every time a speech segments ends it sends 'speech_end()' commands.

    These commands has to be properly detected in the output stream by the following component.
    """

    def __init__(self, cfg, commands, audio_recorded_in, audio_played_in, audio_out):
        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.commands = commands
        self.audio_recorded_in = audio_recorded_in
        self.audio_played_in = audio_played_in
        self.audio_out = audio_out

        self.output_file_name = None
        self.wf = None  # wave file for logging

        if self.cfg['VAD']['type'] == 'power':
            self.vad = PVAD.PowerVAD(cfg)
        elif self.cfg['VAD']['type'] == 'gmm':
            self.vad = GVAD.GMMVAD(cfg)
        else:
            raise ASRException(
                'Unsupported VAD engine: %s' % (self.cfg['VAD']['type'], ))

        # stores information about each frame whether it was classified as speech or non speech
        self.detection_window_speech = deque(
            maxlen=self.cfg['VAD']['decision_frames_speech'])
        self.detection_window_sil = deque(
            maxlen=self.cfg['VAD']['decision_frames_sil'])
        self.deque_audio_recorded_in = deque(
            maxlen=self.cfg['VAD']['speech_buffer_frames'])
        self.deque_audio_played_in = deque(
            maxlen=self.cfg['VAD']['speech_buffer_frames'])

        # keeps last decision about whether there is speech or non speech
        self.last_vad = False

    def process_pending_commands(self):
        """Process all pending commands.

        Available aio_com:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.

        Return True if the process should terminate.
        """

        if self.commands.poll():
            command = self.commands.recv()
            if self.cfg['VAD']['debug']:
                self.cfg['Logging']['system_logger'].debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    # stop recording and playing
                    if self.wf:
                        self.wf.close()

                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in in input buffers
                    while self.audio_recorded_in.poll():
                        data_play = self.audio_recorded_in.recv()
                    while self.audio_played_in.poll():
                        data_play = self.audio_played_in.recv()

                    self.deque_audio_recorded_in.clear()
                    self.deque_audio_played_in.clear()

                    return False

        return False

    def smoothe_decison(self, decision):
        self.detection_window_speech.append(decision)
        self.detection_window_sil.append(decision)

        speech = float(sum(
            self.detection_window_speech)) / len(self.detection_window_speech)
        sil = float(
            sum(self.detection_window_sil)) / len(self.detection_window_sil)
        if self.cfg['VAD']['debug']:
            self.cfg['Logging']['system_logger'].debug(
                'SPEECH: %s SIL: %s' % (speech, sil))

        vad = self.last_vad
        change = None
        if self.last_vad:
            # last decision was speech
            if sil < self.cfg['VAD']['decision_non_speech_threshold']:
                vad = False
                change = 'non-speech'
        else:
            if speech > self.cfg['VAD']['decision_speech_threshold']:
                vad = True
                change = 'speech'

        self.last_vad = vad

        return vad, change

    def read_write_audio(self):
        # read input audio
        while self.audio_recorded_in.poll():
            # read recorded audio
            data_rec = self.audio_recorded_in.recv()

            if isinstance(data_rec, Frame):
                # read played audio
                if self.audio_played_in.poll():
                    data_played = self.audio_played_in.recv()
                else:
                    data_played = Frame(b"\x00" * len(data_rec))

                # buffer the recorded and played audio
                self.deque_audio_recorded_in.append(data_rec)
                self.deque_audio_played_in.append(data_played)

                decison = self.vad.decide(data_rec.payload)
                vad, change = self.smoothe_decison(decison)

                if self.cfg['VAD']['debug']:
                    self.cfg['Logging']['system_logger'].debug(
                        "vad: %s change:%s" % (vad, change))

                if change:
                    if change == 'speech':
                        # inform both the parent and the consumer
                        self.audio_out.send(
                            Command('speech_start()', 'VAD', 'AudioIn'))
                        self.commands.send(
                            Command('speech_start()', 'VAD', 'HUB'))
                        # create new logging file
                        self.output_file_name = os.path.join(
                            self.cfg['Logging'][
                                'system_logger'].get_session_dir_name(),
                            'vad-' + datetime.now().isoformat('-').replace(':', '-') + '.wav')

                        if self.cfg['VAD']['debug']:
                            self.cfg['Logging']['system_logger'].debug('Output file name: %s' % self.output_file_name)

                        self.wf = wave.open(self.output_file_name, 'w')
                        self.wf.setnchannels(2)
                        self.wf.setsampwidth(2)
                        self.wf.setframerate(self.cfg['Audio']['sample_rate'])

                    if change == 'non-speech':
                        # inform both the parent and the consumer
                        self.audio_out.send(
                            Command('speech_end()', 'VAD', 'AudioIn'))
                        self.commands.send(
                            Command('speech_end()', 'VAD', 'HUB'))
                        # close the current logging file
                        if self.wf:
                            self.wf.close()

                if self.cfg['VAD']['debug']:
                    if vad:
                        self.cfg['Logging']['system_logger'].debug('+')
                    else:
                        self.cfg['Logging']['system_logger'].debug('-')

                if vad:
                    while self.deque_audio_recorded_in:
                        # send or save all potentially queued data
                        # when there is change to speech there will be several frames of audio
                        #   if there is no change then there will be only one queued frame

                        data_rec = self.deque_audio_recorded_in.popleft()
                        data_played = self.deque_audio_played_in.popleft()

                        # send the result
                        self.audio_out.send(data_rec)

                        # save the recorded and played data
                        data_stereo = bytearray()
                        for i in range(self.cfg['Audio']['samples_per_frame']):
                            data_stereo.extend(data_rec[i * 2])
                            data_stereo.extend(data_rec[i * 2 + 1])
                            # there might not be enough data to be played
                            # then add zeros
                            try:
                                data_stereo.extend(data_played[i * 2])
                            except IndexError:
                                data_stereo.extend(b'\x00')

                            try:
                                data_stereo.extend(data_played[i * 2 + 1])
                            except IndexError:
                                data_stereo.extend(b'\x00')

                        self.wf.writeframes(data_stereo)

    def run(self):
        while 1:
            time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

            # process all pending commands
            if self.process_pending_commands():
                return

            # process audio data
            self.read_write_audio()
