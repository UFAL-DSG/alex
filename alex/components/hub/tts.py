#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time
import sys
import traceback
import select

READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR


import alex.utils.various as various

from alex.components.hub.messages import Command, Frame, TTSText
from alex.components.tts import TTSException
from alex.components.tts.common import get_tts_type, tts_factory

from alex.utils.procname import set_proc_name


class TTS(multiprocessing.Process):
    """ TTS synthesizes input text and returns speech audio signal.

    This component is a wrapper around multiple TTS engines which handles multiprocessing
    communication.
    """

    def __init__(self, cfg, commands, text_in, audio_out):
        multiprocessing.Process.__init__(self)

        self.exit = False

        self.cfg = cfg
        self.commands = commands
        self.text_in = text_in
        self.audio_out = audio_out

        self.poll = select.poll()

        self.fd_map = {}
        for fd in [self.commands, self.text_in]:
            self.fd_map[fd.fileno()] = fd
            self.poll.register(fd, READ_ONLY)

        tts_type = get_tts_type(cfg)
        self.tts = tts_factory(tts_type, cfg)


    def synthesize(self, user_id, text):
        self.commands.send(Command('tts_start(user_id="%s",text="%s")' %
                           (user_id, text.encode('utf8')), 'TTS', 'HUB'))

        wav = self.tts.synthesize(text.encode('utf8'))

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
                    self.exit = True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in in input buffers
                    while self.text_in.poll():
                        data_in = self.text_in.recv()

                if command.parsed['__name__'] == 'synthesize':
                    self.synthesize(
                        command.parsed['user_id'], command.parsed['text'])

        return False

    def read_text_write_audio(self):
        # read input audio
        stack = []
        while self.text_in.poll():
            stack.append(self.text_in.recv())

        data_tts = stack[-1]
        if isinstance(data_tts, TTSText):
            self.synthesize(None, data_tts.text)

    def wait_for_message(self):
        # block until a message is ready
        ready = self.poll.poll()

        # process each available message
        for fd, event in ready:
            fd_obj = self.fd_map[fd]

            if fd_obj == self.text_in:
                self.read_text_write_audio()
            elif fd_obj == self.commands:
                self.process_pending_commands()



    def run(self):
        self.command = None
        set_proc_name("alex_TTS")

        while not self.exit:
            try:
                self.wait_for_message()
            except Exception:
                traceback.print_exc()
                import alex.utils.rdb as rdb; rdb.set_trace()