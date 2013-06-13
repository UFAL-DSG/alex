#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

if __name__ == "__main__":
    import autopath

import multiprocessing
import time
import traceback

import alex.components.asr.google as GASR
import alex.components.asr.julius as JASR

from alex.components.asr.exception import ASRException
from alex.components.asr.julius import JuliusASRTimeoutException
from alex.components.asr.utterance import UtteranceNBList, \
    UtteranceConfusionNetwork
from alex.components.hub.messages import Command, Frame, ASRHyp

from alex.utils.procname import set_proc_name


class ASR(multiprocessing.Process):
    """\
    ASR recognizes input audio and returns an N-best list hypothesis or
    a confusion network.

    Recognition starts with the "speech_start()" command in the input audio
    stream and ends with the "speech_end()" command.

    When the "speech_end()" command is received, the component asks responsible
    ASR module to return hypotheses and sends them to the output.

    This component is a wrapper around multiple recognition engines which
    handles inter-process communication.

    Attributes:
        asr -- the ASR object itself

    """

    def __init__(self, cfg, commands, audio_in, asr_hypotheses_out):
        """\
        Initialises an ASR object according to the configuration (cfg['ASR']
        is the relevant section), and stores pipe ends to other processes.

        Arguments:
            cfg: a Config object specifying the configuration to use
            commands: our end of a pipe (multiprocessing.Pipe) for receiving
                commands
            audio_in: our end of a pipe (multiprocessing.Pipe) for receiving
                audio frames (from VAD)
            asr_hypotheses_out: our end of a pipe (multiprocessing.Pipe) for
                sending ASR hypotheses

        """

        multiprocessing.Process.__init__(self)

        self.cfg = cfg
        self.commands = commands
        self.audio_in = audio_in
        self.asr_hypotheses_out = asr_hypotheses_out

        self.asr = None
        if self.cfg['ASR']['type'] == 'Google':
            self.asr = GASR.GoogleASR(cfg)
        elif self.cfg['ASR']['type'] == 'Julius':
            self.asr = JASR.JuliusASR(cfg)
        else:
            raise ASRException(
                'Unsupported ASR engine: %s' % (self.cfg['ASR']['type'], ))

        self.system_logger = self.cfg['Logging']['system_logger']
        self.session_logger = self.cfg['Logging']['session_logger']

    def process_pending_commands(self):
        """Process all pending commands.

        Available commands:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.

        Returns True iff the process should terminate.
        """

        if self.commands.poll():
            command = self.commands.recv()
            if self.cfg['ASR']['debug']:
                self.system_logger.debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    return True

                if command.parsed['__name__'] == 'flush':
                    # Discard all data in input buffers.
                    while self.audio_in.poll():
                        self.audio_in.recv()

                    self.asr.flush()

                    return False

        return False

    def read_audio_write_asr_hypotheses(self):
        # Read input audio.
        while self.audio_in.poll():
            # Read recorded audio.
            data_rec = self.audio_in.recv()

            if isinstance(data_rec, Frame):
                if self.recognition_on:
                    self.asr.rec_in(data_rec)
            elif isinstance(data_rec, Command):
                dr_speech_start = False

                if data_rec.parsed['__name__'] == "speech_start":
                    dr_speech_start = "speech_start"
                elif data_rec.parsed['__name__'] == "speech_end":
                    dr_speech_start = "speech_end"

                # Check consistency of the input command.
                if dr_speech_start:
                    if ((not self.recognition_on
                            and dr_speech_start != "speech_start")
                        or
                        (self.recognition_on
                            and dr_speech_start != "speech_end")):
                        msg = ('Commands received by the ASR component are '
                               'inconsistent (recognition_on: {rec}; the new '
                               'command: {cmd}').format(
                                   rec=self.recognition_on,
                                   cmd=dr_speech_start)
                        raise ASRException(msg)

                if dr_speech_start == "speech_start":
                    self.commands.send(Command("asr_start()", 'ASR', 'HUB'))
                    self.recognition_on = True

                    if self.cfg['ASR']['debug']:
                        self.system_logger.debug('ASR: speech_start()')

                elif dr_speech_start == "speech_end":
                    self.recognition_on = False

                    if self.cfg['ASR']['debug']:
                        self.system_logger.debug('ASR: speech_end()')

                    try:
                        asr_hyp = self.asr.hyp_out()

                        if self.cfg['ASR']['debug']:
                            msg = list()
                            msg.append("ASR Hypothesis")
                            msg.append("-" * 60)
                            msg.append(unicode(asr_hyp))
                            msg.append(u"")
                            msg = u'\n'.join(msg)
                            self.system_logger.debug(msg)

                    except (ASRException, JuliusASRTimeoutException):
                        self.system_logger.debug("Julius ASR Result Timeout.")
                        if self.cfg['ASR']['debug']:
                            msg = list()
                            msg.append("ASR Alternative hypothesis")
                            msg.append("-" * 60)
                            msg.append("sil")
                            msg.append("")
                            msg = u'\n'.join(msg)
                            self.system_logger.debug(msg)

                        asr_hyp = UtteranceConfusionNetwork()
                        asr_hyp.add([[1.0, "sil"], ])

                    # The ASR component can return either NBList or a confusion
                    # network.
                    if isinstance(asr_hyp, UtteranceNBList):
                        self.session_logger.asr("user", asr_hyp, None)
                    elif isinstance(asr_hyp, UtteranceConfusionNetwork):
                        self.session_logger.asr("user",
                                                asr_hyp.get_utterance_nblist(),
                                                asr_hyp)
                    else:
                        self.session_logger.asr("user", [(-1, asr_hyp)], None)

                    self.commands.send(Command("asr_end()", 'ASR', 'HUB'))
                    self.asr_hypotheses_out.send(ASRHyp(asr_hyp))
            else:
                raise ASRException('Unsupported input.')

    def run(self):
        self.recognition_on = False
        set_proc_name("Alex_ASR")

        while 1:
            try:
                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                # Process all pending commands.
                if self.process_pending_commands():
                    return

                # Process audio data.
                self.read_audio_write_asr_hypotheses()
            except Exception:
                traceback.print_exc()
