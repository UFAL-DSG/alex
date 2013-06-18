#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import deque
from datetime import datetime
import multiprocessing
import os.path
import sys
import os
import time
import wave

from alex.components.asr.exception import ASRException
from alex.components.hub.messages import Command, Frame
from alex.utils.procname import set_proc_name
from alex.utils.sessionlogger import SessionClosedException

import alex.components.vad.power as PVAD
import alex.components.vad.gmm as GVAD


class VAD(multiprocessing.Process):
    """ VAD detects segments of speech in the audio stream.

    It implements two smoothing windows, one for detection of speech and one
    for detection of silence.

    1) The speech window is typically shorter so that the detection if more
       responsive towards the speech, it is easy to activate for the speech.
    2) The silence windows should be longer so that short pauses are not
       triggered and only one speech segment including the short pauses is
       generated.

    It process input signal and outputs only frames with speech. Every time
    a new speech segment starts, it sends 'speech_start()' and every time
    a speech segments ends, it sends 'speech_end()' commands.

    These commands have to be properly detected in the output stream by the
    following component.

    """

    def __init__(self, cfg, commands, audio_recorded_in, audio_out):
        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.system_logger = cfg['Logging']['system_logger']
        self.session_logger = cfg['Logging']['session_logger']
        self.commands = commands
        self.audio_recorded_in = audio_recorded_in
        self.audio_out = audio_out

        self.output_file_name = None
        self.wf = None  # wave file for logging

        if self.cfg['VAD']['type'] == 'power':
            self.vad = PVAD.PowerVAD(cfg)
        elif self.cfg['VAD']['type'] == 'gmm':
            self.vad = GVAD.GMMVAD(cfg)
        else:
            raise ASRException('Unsupported VAD engine: %s' % (self.cfg['VAD']['type'], ))

        # stores information about each frame whether it was classified as
        # speech or non speech
        self.detection_window_speech = \
                deque(maxlen=self.cfg['VAD']['decision_frames_speech'])
        self.detection_window_sil = \
                deque(maxlen=self.cfg['VAD']['decision_frames_sil'])
        self.deque_audio_recorded_in = \
                deque(maxlen=self.cfg['VAD']['speech_buffer_frames'])

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
                self.system_logger.debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    # Stop recording and playing.
                    if self.wf:
                        self.wf.close()

                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in in input buffers
                    while self.audio_recorded_in.poll():
                        data_play = self.audio_recorded_in.recv()

                    self.detection_window_speech.clear()
                    self.detection_window_sil.clear()
                    self.deque_audio_recorded_in.clear()

                    # reset other state variables
                    self.last_vad = False

                    return False

        return False

    def smoothe_decison(self, decision):
        self.detection_window_speech.append(decision)
        self.detection_window_sil.append(decision)

        speech = float(sum(self.detection_window_speech)) / (len(self.detection_window_speech) + 1.0)
        sil = float(sum(self.detection_window_sil)) / (len(self.detection_window_sil) + 1.0)
        if self.cfg['VAD']['debug']:
            self.system_logger.debug('SPEECH: %s SIL: %s' % (speech, sil))

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
                # buffer the recorded and played audio
                self.deque_audio_recorded_in.append(data_rec)

                decision = self.vad.decide(data_rec.payload)
                vad, change = self.smoothe_decison(decision)

                if self.cfg['VAD']['debug']:
                    self.system_logger.debug("vad: %s change:%s" % (vad, change))

                if change:
                    if change == 'speech':
                        # Create new wave file.
                        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f')
                        self.output_file_name = os.path.join(self.system_logger.get_session_dir_name(),
                            'vad-{stamp}.wav'.format(stamp=timestamp))

                        self.session_logger.turn("user")
                        self.session_logger.rec_start("user", os.path.basename(self.output_file_name))

                        # Inform both the parent and the consumer.
                        self.audio_out.send(Command('speech_start(fname="%s")' % os.path.basename(self.output_file_name),
                                                    'VAD', 'AudioIn'))
                        self.commands.send(Command('speech_start(fname="%s")' % os.path.basename(self.output_file_name),
                                                    'VAD', 'HUB'))

                        if self.cfg['VAD']['debug']:
                            self.system_logger.debug('Output file name: %s' % self.output_file_name)

                        self.wf = wave.open(self.output_file_name, 'w')
                        self.wf.setnchannels(1)
                        self.wf.setsampwidth(2)
                        self.wf.setframerate(self.cfg['Audio']['sample_rate'])

                    elif change == 'non-speech':
                        # Log the change.
                        # if self.session_logger.is_open:
                        if self.cfg['VAD']['debug']:
                            self.system_logger.debug('REC END Output file name: {out}'.format(out=self.output_file_name))
                        self.session_logger.rec_end(os.path.basename(self.output_file_name))

                        # Inform both the parent and the consumer.
                        self.audio_out.send(Command('speech_end(fname="%s")' % os.path.basename(self.output_file_name),
                            'VAD', 'AudioIn'))
                        self.commands.send(Command('speech_end(fname="%s")' % os.path.basename(self.output_file_name),
                            'VAD', 'HUB'))
                        # Close the current wave file.
                        if self.wf:
                            self.wf.close()

                if self.cfg['VAD']['debug']:
                    if vad:
                        self.system_logger.debug('+')
                    else:
                        self.system_logger.debug('-')

                if vad:
                    while self.deque_audio_recorded_in:
                        # Send or save all potentially queued data.
                        #   - When there is change to speech, there will be
                        #     several frames of audio;
                        #   - If there is no change, then there will be only
                        #     one queued frame.

                        data_rec = self.deque_audio_recorded_in.popleft()

                        # Send the result.
                        self.audio_out.send(data_rec)

                        # Save the recorded data.
                        # data_stereo = bytearray()
                        # for i in range(self.cfg['Audio']['samples_per_frame']):
                        #     data_stereo.extend(data_rec[i * 2])
                        #     data_stereo.extend(data_rec[i * 2 + 1])

                        # If the wave file has already been closed,
                        if self.wf._file is None:
                            # Prevent the exception from being raised next
                            # time (or try to achieve that).
                            self.last_vad = False
                            # Raise the exception.
                            # FIXME: It should be a different one. It is not
                            # the session file that is closed, but the wave
                            # file.
                            raise SessionClosedException("The output wave "
                                "file has already been closed.")
                        self.wf.writeframes(bytearray(data_rec))

    def run(self):
        set_proc_name("alex_VAD")

        try:
            while 1:
                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                # Process all pending commands.
                if self.process_pending_commands():
                    return

                # FIXME: Make the following test work.
                # # Wait until a session has started.
                # if self.session_logger.is_open:
                # Process audio data.
                try:
                    self.read_write_audio()
                except SessionClosedException as ex:
                    self.system_logger.exception('VAD:read_write_audio: {ex!s}'
                                                    .format(ex=ex))
                # FIXME: Make the following test work.
                # # Wait until a session has started.
                # if self.session_logger.is_open:
                # Process audio data.
                try:
                    self.read_write_audio()
                except SessionClosedException as ex:
                    self.system_logger.exception('VAD:read_write_audio: {ex!s}'\
                                                 .format(ex=ex))
        except: 
            print "Unexpected error:", sys.exc_info()          
            print "Exiting!"
            os._exit(1)
