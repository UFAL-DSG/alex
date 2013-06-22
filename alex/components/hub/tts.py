#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import multiprocessing
import time
import sys
import traceback
import os
import string

from datetime import datetime

from alex.components.hub.messages import Command, Frame, TTSText
from alex.components.tts.common import get_tts_type, tts_factory

from alex.utils.procname import set_proc_name
from alex.utils.audio import save_wav
import alex.utils.various as various


class TTS(multiprocessing.Process):
    """TTS synthesizes input text and returns speech audio signal.

    This component is a wrapper around multiple TTS engines which handles multiprocessing
    communication.
    """

    def __init__(self, cfg, commands, text_in, audio_out, close_event):
        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.commands = commands
        self.text_in = text_in
        self.audio_out = audio_out
        self.close_event = close_event

        tts_type = get_tts_type(cfg)
        self.tts = tts_factory(tts_type, cfg)

    def get_wav_name(self):
        """ Generates a new wave name for the TTS output.

        Returns the full path and the base name.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f')
        fname = os.path.join(self.cfg['Logging']['system_logger'].get_session_dir_name(),
                             'tts-{stamp}.wav'.format(stamp=timestamp))

        return fname, os.path.basename(fname)

    def parse_into_segments(self, text):
        segments = []
        last_split = 0
        lc = [c for c in string.lowercase]
        lc.extend('ěščřžýáíé')
        up = [c for c in string.uppercase]
        up.extend('ĚŠČČŘŽÝÁÍÉ')

        for i in range(1, len(text)-2):
            if (text[i-1] in lc
                and text[i] in ['.', ",", "?"]
                and text[i+1] == " "
                and text[i+2] in up):
                segments.append(text[last_split:i+1])
                last_split = i + 2
        else:
            segments.append(text[last_split:])

        return segments

    def remove_final_silence(self, wav):
        for i, x in enumerate(reversed(wav)):
            if ord(x) != 0:
                break

        return wav[:-int(i*self.cfg['TTS']['final_silence_removal_proportion']) - 1]

    def synthesize(self, user_id, text):
        wav = []
        fname, bn = self.get_wav_name()

        self.commands.send(Command('tts_start(user_id="%s",text="%s")' % (user_id, text), 'TTS', 'HUB'))
        self.audio_out.send(Command('utterance_start(user_id="%s",text="%s",fname="%s")' %
                            (user_id, text, bn), 'TTS', 'AudioOut'))

        segments = self.parse_into_segments(text)

        for segment_text in segments:
            segment_wav = self.tts.synthesize(segment_text)
            segment_wav = self.remove_final_silence(segment_wav)
            wav.append(segment_wav)

            segment_wav = various.split_to_bins(segment_wav, 2 * self.cfg['Audio']['samples_per_frame'])

            for frame in segment_wav:
                self.audio_out.send(Frame(frame))

        self.audio_out.send(Command('utterance_end(user_id="%s",text="%s",fname="%s")' %
                            (user_id, text, bn), 'TTS', 'AudioOut'))

        self.commands.send(Command('tts_end(user_id="%s",text="%s",fname="%s")' %
                           (user_id, text, bn), 'TTS', 'HUB'))

        save_wav(self.cfg, fname, b"".join(wav))

    def process_pending_commands(self):
        """Process all pending commands.

        Available aio_com:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.

        Return True if the process should terminate.
        """

        while self.commands.poll():
            command = self.commands.recv()
            if self.cfg['TTS']['debug']:
                self.cfg['Logging']['system_logger'].debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in in input buffers
                    while self.text_in.poll():
                        data_in = self.text_in.recv()

                    self.commands.send(Command("flushed()", 'TTS', 'HUB'))
                    
                    return False

                if command.parsed['__name__'] == 'synthesize':
                    self.synthesize(command.parsed['user_id'], command.parsed['text'])

                    return False

        return False

    def read_text_write_audio(self):
        # read only one TTS command so that the others can be flushed in it is requested
        # between the processing of the TTS commands
        # REMEMBER: processing of one TTS command can take a lot of time

        if self.text_in.poll():
            data_tts = self.text_in.recv()
            if isinstance(data_tts, TTSText):
                self.synthesize(None, data_tts.text)

    def run(self):
        try:
            self.command = None
            set_proc_name("alex_TTS")

            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    return

                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                # process all pending commands
                if self.process_pending_commands():
                    return

                # process audio data
                self.read_text_write_audio()
        except:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the TTS process.')
            self.close_event.set()
            raise

