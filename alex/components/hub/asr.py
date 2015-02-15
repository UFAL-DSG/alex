#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

if __name__ == "__main__":
    import autopath

from collections import deque
import multiprocessing
import time

from alex.components.asr.common import asr_factory
from alex.components.asr.exceptions import ASRException
from alex.components.asr.utterance import UtteranceNBList, UtteranceConfusionNetwork
from alex.components.hub.messages import Command, Frame, ASRHyp
from alex.utils.procname import set_proc_name


class ASR(multiprocessing.Process):

    """
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

    def __init__(self, cfg, commands, audio_in, asr_hypotheses_out, close_event):
        """
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
        self.local_commands = deque()
        self.audio_in = audio_in
        self.local_audio_in = deque()
        self.asr_hypotheses_out = asr_hypotheses_out
        self.close_event = close_event

        # Load the ASR
        self.asr = asr_factory(cfg)

        self.system_logger = self.cfg['Logging']['system_logger']
        self.session_logger = self.cfg['Logging']['session_logger']

        self.recognition_on = False

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

        Available commands:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.

        Returns True iff the process should terminate.
        """

        while self.local_commands:
            command = self.local_commands.popleft()
            if self.cfg['ASR']['debug']:
                self.system_logger.debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    return True

                if command.parsed['__name__'] == 'flush':
                    # Discard all data in input buffers.
                    while self.audio_in.poll():
                        self.audio_in.recv()

                    self.local_audio_in.clear()
                    self.asr.flush()
                    self.recognition_on = False

                    self.commands.send(Command("flushed()", 'ASR', 'HUB'))

                    return False

        return False

    def read_audio_write_asr_hypotheses(self):
        # Read input audio.
        if self.local_audio_in:
            if len(self.local_audio_in) > 40:
                print "ASR unprocessed frames:", len(self.local_audio_in)

            if len(self.local_audio_in) > 200:
                print "ASR too many unprocessed frames:", len(self.local_audio_in)
                print "    skipping everything until the end of the segment:", len(self.local_audio_in)
                while len(self.local_audio_in) > 2 and isinstance(self.local_audio_in[0], Frame):
                    skip = self.local_audio_in.popleft()

            # read recorded audio
            data_rec = self.local_audio_in.popleft()

            if isinstance(data_rec, Frame):
                if self.recognition_on:
                    self.asr.rec_in(data_rec)
            elif isinstance(data_rec, Command):
                dr_speech_start = False
                fname = None

                if data_rec.parsed['__name__'] == "speech_start":
                    # check whether there are more then one speech segments
                    segments = [ cmd for cmd in self.local_audio_in
                                 if isinstance(cmd, Command) and cmd.parsed['__name__'] == "speech_start"]
                    if len(segments):
                        # there are multiple unprocessed segments in the queue
                        # remove all unprocessed segments except the last
                        print "ASR too many unprocessed speech segments:", len(segments)
                        print "    removed all segments but the last"
                        removed_segments = 0
                        while removed_segments < len(segments):
                            data_rec = self.local_audio_in.popleft()
                            if isinstance(data_rec, Command) and data_rec.parsed['__name__'] == "speech_start":
                                removed_segments += 1

                    dr_speech_start = "speech_start"
                    fname = data_rec.parsed['fname']
                elif data_rec.parsed['__name__'] == "speech_end":
                    dr_speech_start = "speech_end"
                    fname = data_rec.parsed['fname']

                # Check consistency of the input command.
                if dr_speech_start:
                    if ((not self.recognition_on and dr_speech_start != "speech_start")
                        or
                        (self.recognition_on and dr_speech_start != "speech_end")):
                        msg = ('Commands received by the ASR component are '
                               'inconsistent (recognition_on: {rec}; the new '
                               'command: {cmd}').format(
                                   rec=self.recognition_on,
                                   cmd=dr_speech_start)
                        self.system_logger.exception(msg)

                if dr_speech_start == "speech_start":
                    self.commands.send(Command('asr_start(fname="%s")' % fname, 'ASR', 'HUB'))
                    self.recognition_on = True

                    if self.cfg['ASR']['debug']:
                        self.system_logger.debug('ASR: speech_start(fname="%s")' % fname)

                elif dr_speech_start == "speech_end":
                    self.recognition_on = False

                    if self.cfg['ASR']['debug']:
                        self.system_logger.debug('ASR: speech_end(fname="%s")' % fname)

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
                        asr_hyp.add([[1.0, "_other_"], ])

                    # The ASR component can return either NBList or a confusion
                    # network.
                    if isinstance(asr_hyp, UtteranceNBList):
                        self.session_logger.asr("user", fname, asr_hyp, None)
                    elif isinstance(asr_hyp, UtteranceConfusionNetwork):
                        self.session_logger.asr("user", fname, asr_hyp.get_utterance_nblist(), asr_hyp)
                    else:
                        self.session_logger.asr("user", fname, [(-1, asr_hyp)], None)

                    self.commands.send(Command('asr_end(fname="%s")' % fname, 'ASR', 'HUB'))
                    self.asr_hypotheses_out.send(ASRHyp(asr_hyp, fname=fname))
            else:
                raise ASRException('Unsupported input.')

    def run(self):
        try:
            set_proc_name("Alex_ASR")
            self.cfg['Logging']['session_logger'].cancel_join_thread()

            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    print 'Received close event in: %s' % multiprocessing.current_process().name
                    return

                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                s = (time.time(), time.clock())

                self.recv_input_locally()

                # Process all pending commands.
                if self.process_pending_commands():
                    return

                # Process audio data.
                for i in range(self.cfg['ASR']['n_rawa']):
                    self.read_audio_write_asr_hypotheses()

                d = (time.time() - s[0], time.clock() - s[1])
                if d[0] > 0.200:
                    print "EXEC Time inner loop: ASR t = {t:0.4f} c = {c:0.4f}\n".format(t=d[0], c=d[1])

        except KeyboardInterrupt:
            print 'KeyboardInterrupt exception in: %s' % multiprocessing.current_process().name
            self.close_event.set()
            return
        except:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in ASR process.')
            self.close_event.set()
            raise

        print 'Exiting: %s. Setting close event' % multiprocessing.current_process().name
        self.close_event.set()
