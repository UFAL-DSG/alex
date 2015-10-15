#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time

from collections import deque
from datetime import datetime

from alex.components.asr.exceptions import ASRException
from alex.components.hub.messages import Command, Frame
from alex.utils.procname import set_proc_name
from alex.utils.exceptions import SessionClosedException

import alex.components.vad.power as PVAD
import alex.components.vad.gmm as GVAD
import alex.components.vad.ffnn as NNVAD

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

    def __init__(self, cfg, commands, audio_in, audio_out, close_event):
        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.system_logger = cfg['Logging']['system_logger']
        self.session_logger = cfg['Logging']['session_logger']
        self.commands = commands
        self.local_commands = deque()
        self.audio_in = audio_in
        self.local_audio_in = deque()
        self.audio_out = audio_out
        self.close_event = close_event

        self.vad_fname = None

        if self.cfg['VAD']['type'] == 'power':
            self.vad = PVAD.PowerVAD(cfg)
        elif self.cfg['VAD']['type'] == 'gmm':
            self.vad = GVAD.GMMVAD(cfg)
        elif self.cfg['VAD']['type'] == 'ffnn':
            self.vad = NNVAD.FFNNVAD(cfg)
        else:
            raise ASRException('Unsupported VAD engine: %s' % (self.cfg['VAD']['type'], ))

        # stores information about each frame whether it was classified as speech or non speech
        self.detection_window_speech = deque(maxlen=self.cfg['VAD']['decision_frames_speech'])
        self.detection_window_sil    = deque(maxlen=self.cfg['VAD']['decision_frames_sil'])
        self.deque_audio_in          = deque(maxlen=self.cfg['VAD']['speech_buffer_frames'])

        # keeps last decision about whether there is speech or non speech
        self.last_vad = False

    def recv_input_locally(self):
        """ Copy all input from input connections into local queue objects.

        This will prevent blocking the senders.
        """

        while self.commands.poll():
            command = self.commands.recv()
            self.local_commands.append(command)

        while self.audio_in.poll():
            frame = self.audio_in.recv()
            self.local_audio_in.append(frame)

    def process_pending_commands(self):
        """Process all pending commands.

        Available aio_com:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.

        Return True if the process should terminate.

        """

        while self.local_commands:
            command = self.local_commands.popleft()
            #if self.cfg['VAD']['debug']:
            self.system_logger.debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in in input buffers
                    while self.audio_in.poll():
                        data_play = self.audio_in.recv()

                    self.local_audio_in.clear()
                    self.detection_window_speech.clear()
                    self.detection_window_sil.clear()
                    self.deque_audio_in.clear()

                    # reset other state variables
                    self.last_vad = False

                    self.commands.send(Command("flushed()", 'VAD', 'HUB'))

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
        if self.local_audio_in:
            if len(self.local_audio_in) > 10:
                print "VAD unprocessed frames:", len(self.local_audio_in)
                self.local_audio_in = deque(list(self.local_audio_in)[-10:])

            # read recorded audio
            data_rec = self.local_audio_in.popleft()

            if isinstance(data_rec, Frame):
                # buffer the recorded and played audio
                self.deque_audio_in.append(data_rec)

                #s = (time.time(), time.clock())

                decision = self.vad.decide(data_rec.payload)
                vad, change = self.smoothe_decison(decision)

                #d = (time.time() - s[0], time.clock() - s[1])
                #if d[0] > 0.001:
                #    print "VAD t = {t:0.4f} c = {c:0.4f}\n".format(t=d[0], c=d[1])

                if self.cfg['VAD']['debug']:
                    self.system_logger.debug("vad: %s change: %s" % (vad, change))

                    if vad:
                        self.system_logger.debug('+')
                    else:
                        self.system_logger.debug('-')

                if change == 'speech':
                    # Create new wave file.
                    timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S.%f')
                    self.vad_fname = 'vad-{stamp}.wav'.format(stamp=timestamp)

                    self.session_logger.turn("user")
                    self.session_logger.rec_start("user", self.vad_fname)

                    # Inform both the parent and the consumer.
                    self.audio_out.send(Command('speech_start(fname="%s")' % self.vad_fname, 'VAD', 'AudioIn'))
                    self.commands.send(Command('speech_start(fname="%s")' % self.vad_fname, 'VAD', 'HUB'))

                elif change == 'non-speech':
                    self.session_logger.rec_end(self.vad_fname)

                    # Inform both the parent and the consumer.
                    self.audio_out.send(Command('speech_end(fname="%s")' % self.vad_fname, 'VAD', 'AudioIn'))
                    self.commands.send(Command('speech_end(fname="%s")' % self.vad_fname, 'VAD', 'HUB'))

                if vad:
                    while self.deque_audio_in:
                        # Send or save all potentially queued data.
                        #   - When there is change to speech, there will be
                        #     several frames of audio;
                        #   - If there is no change, then there will be only
                        #     one queued frame.

                        data_rec = self.deque_audio_in.popleft()

                        # Send the result.
                        self.audio_out.send(data_rec)
                        self.session_logger.rec_write(self.vad_fname, data_rec)

    def run(self):
        try:
            set_proc_name("Alex_VAD")
            self.session_logger.cancel_join_thread()

            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    print 'Received close event in: %s' % multiprocessing.current_process().name
                    return

                if not self.local_audio_in:
                    time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                s = (time.time(), time.clock())

                self.recv_input_locally()

                # Process all pending commands.
                if self.process_pending_commands():
                    return

                # FIXME: Make the following test work.
                # # Wait until a session has started.
                # if self.session_logger.is_open:
                # Process audio data.
                try:
                    for i in range(self.cfg['VAD']['n_rwa']):
                        # process at least n_rwa frames
                        self.read_write_audio()
                except SessionClosedException as e:
                    self.system_logger.exception('VAD:read_write_audio: {ex!s}'.format(ex=e))

                d = (time.time() - s[0], time.clock() - s[1])
                if d[0] > 0.100:
                    print "VAD t = {t:0.4f} c = {c:0.4f}\n".format(t=d[0], c=d[1])
        except KeyboardInterrupt:
            print 'KeyboardInterrupt exception in: %s' % multiprocessing.current_process().name
            self.close_event.set()
            return
        except:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the VAD process.')
            self.close_event.set()
            raise
