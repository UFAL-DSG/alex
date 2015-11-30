#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import multiprocessing
import time
import sys
import traceback
import os
import string
import struct

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

    def parse_into_segments(self, text):
        segments = []
        last_split = 0
        lc = [c for c in string.lowercase]
        lc.extend('ěščřžýáíéňťďůú')
        up = [c for c in string.uppercase]
        up.extend('ĚŠČŘŽÝÁÍÉŇŤĎŮÚ')

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

    def remove_start_and_final_silence(self, wav):
        """ Removes silence at the beginning and the end of the provided wave audio signal.

        :param wav: input wave audio signal
        :return: wave audio signal without the silence at  the beginning and the end
        """

        if len(wav) > 0:
            for i, x in enumerate(wav):
                if ord(x) != 0:
                    break

            for j, x in enumerate(reversed(wav)):
                if ord(x) != 0:
                    break

            return wav[2*int(i/2):-2*int(j/2+1)]
        else:
            return wav

    def gen_silence(self):
        """ Generates the silence wave audio signal with the length given by the global TTS config.

        :return: a silence wave audio signal
        """

        length = int(self.cfg['TTS']['in_between_segments_silence']*self.cfg['Audio']['sample_rate'])

        return struct.pack('h',0)*length

    def synthesize(self, user_id, text, log="true"):
        if text == "_silence_" or text == "silence()":
            # just let the TTS generate an empty wav
            text == ""

        wav = []
        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S.%f')
        fname = 'tts-{stamp}.wav'.format(stamp=timestamp)

        self.commands.send(Command('tts_start(user_id="%s",text="%s",fname="%s")' % (user_id,text,fname), 'TTS', 'HUB'))
        self.audio_out.send(Command('utterance_start(user_id="%s",text="%s",fname="%s",log="%s")' %
                            (user_id, text, fname, log), 'TTS', 'AudioOut'))

        segments = self.parse_into_segments(text)

        for i, segment_text in enumerate(segments):
            segment_wav = self.tts.synthesize(segment_text)
            segment_wav = self.remove_start_and_final_silence(segment_wav)
            if i <  len(segments) - 1:
                # add silence only for non-final segments
                segment_wav += self.gen_silence()

            wav.append(segment_wav)

            segment_wav = various.split_to_bins(segment_wav, 2 * self.cfg['Audio']['samples_per_frame'])

            for frame in segment_wav:
                self.audio_out.send(Frame(frame))

        self.commands.send(Command('tts_end(user_id="%s",text="%s",fname="%s")' % (user_id,text,fname), 'TTS', 'HUB'))
        self.audio_out.send(Command('utterance_end(user_id="%s",text="%s",fname="%s",log="%s")' %
                            (user_id, text, fname, log), 'TTS', 'AudioOut'))

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
                    self.synthesize(command.parsed['user_id'], command.parsed['text'], command.parsed['log'])

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
            set_proc_name("Alex_TTS")
            self.cfg['Logging']['session_logger'].cancel_join_thread()

            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    print 'Received close event in: %s' % multiprocessing.current_process().name
                    return

                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                s = (time.time(), time.clock())

                # process all pending commands
                if self.process_pending_commands():
                    return

                # process audio data
                self.read_text_write_audio()

                d = (time.time() - s[0], time.clock() - s[1])
                if d[0] > 0.200:
                    print "EXEC Time inner loop: TTS t = {t:0.4f} c = {c:0.4f}\n".format(t=d[0], c=d[1])

        except KeyboardInterrupt:
            print 'KeyboardInterrupt exception in: %s' % multiprocessing.current_process().name
            self.close_event.set()
            return
        except:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in the TTS process.')
            self.close_event.set()
            raise

        print 'Exiting: %s. Setting close event' % multiprocessing.current_process().name
        self.close_event.set()
