#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys
import traceback

import SDS.components.tts.google as GTTS
import SDS.components.tts.flite as FTTS
import SDS.components.tts.speechtech as STTS
import SDS.utils.various as various

from SDS.components.hub.messages import Command, Frame, TTSText
from SDS.utils.exception import TTSException

from SDS.utils.procname import set_proc_name


class TTS(multiprocessing.Process):
    """ TTS synthesizes input text and returns speech audio signal.

    This component is a wrapper around multiple TTS engines which handles multiprocessing
    communication.
    """

    def __init__(self, cfg, commands, text_in, audio_out):
        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.commands = commands
        self.text_in = text_in
        self.audio_out = audio_out

        self.tts = None
        if self.cfg['TTS']['type'] == 'Google':
            self.tts = GTTS.GoogleTTS(cfg)
        elif self.cfg['TTS']['type'] == 'Flite':
            self.tts = FTTS.FliteTTS(cfg)
        elif self.cfg['TTS']['type'] == 'SpeechTech':
            self.tts = STTS.SpeechtechTTS(cfg)
        else:
            raise TTSException(
                'Unsupported TTS engine: %s' % (self.cfg['TTS']['type'], ))

    def synthesize(self, user_id, text):
        self.commands.send(Command('tts_start(user_id="%s",text="%s")' %
                           (user_id, text), 'TTS', 'HUB'))

        wav = self.tts.synthesize(text)

        # FIXME: split the wave so that the last bin is of the size of the full frame
        # this bug is at many places in the code
        wav = various.split_to_bins(
            wav, 2 * self.cfg['Audio']['samples_per_frame'])

        self.audio_out.send(Command('utterance_start(user_id="%s",text="%s")' %
                            (user_id, text), 'TTS', 'AudioOut'))
        for frame in wav:
            self.audio_out.send(Frame(frame))
        self.audio_out.send(Command('utterance_end(user_id="%s",text="%s")' %
                            (user_id, text), 'TTS', 'AudioOut'))

        self.commands.send(Command('tts_end(user_id="%s",text="%s")' %
                           (user_id, text), 'TTS', 'HUB'))

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
            if self.cfg['TTS']['debug']:
                self.cfg['Logging']['system_logger'].debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in in input buffers
                    while self.text_in.poll():
                        data_in = self.text_in.recv()

                    return False

                if command.parsed['__name__'] == 'synthesize':
                    self.synthesize(
                        command.parsed['user_id'], command.parsed['text'])

                    return False

        return False

    def read_text_write_audio(self):
        # read input audio
        while self.text_in.poll():
            # read the text be synthesised
            data_tts = self.text_in.recv()

            if isinstance(data_tts, TTSText):
                self.synthesize(None, data_tts.text)

    def run(self):
        self.command = None
        set_proc_name("SDS_TTS")

        while 1:
            time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

            try:
                # process all pending commands
                if self.process_pending_commands():
                    return

                # process audio data
                self.read_text_write_audio()
            except Exception:
                traceback.print_exc()
