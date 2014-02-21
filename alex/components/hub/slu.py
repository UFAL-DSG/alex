#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

import multiprocessing
import time

from alex.components.slu.da import DialogueActNBList, DialogueActConfusionNetwork
from alex.components.hub.messages import Command, ASRHyp, SLUHyp
from alex.components.slu.common import slu_factory
from alex.components.slu.exceptions import SLUException
from alex.utils.procname import set_proc_name


class SLU(multiprocessing.Process):
    """
    The SLU component receives ASR hypotheses and converts them into
    hypotheses about the meaning of the input in the form of dialogue
    acts.

    This component is a wrapper around multiple SLU components which handles
    inter-process communication.
    """

    def __init__(self, cfg, commands, asr_hypotheses_in, slu_hypotheses_out,
                 close_event):
        """
        Initialises an SLU object according to the configuration (cfg['SLU']
        is the relevant section), and stores ends of pipes to other processes.

        Arguments:
            cfg: a Config object specifying the configuration to use
            commands: our end of a pipe (multiprocessing.Pipe) for receiving
                commands
            asr_hypotheses_in: our end of a pipe (multiprocessing.Pipe) for
                receiving audio frames (from ASR)
            slu_hypotheses_out: our end of a pipe (multiprocessing.Pipe) for
                sending SLU hypotheses

        """

        multiprocessing.Process.__init__(self)

        # Save the configuration.
        self.cfg = cfg

        # Save the pipe ends.
        self.commands = commands
        self.asr_hypotheses_in = asr_hypotheses_in
        self.slu_hypotheses_out = slu_hypotheses_out
        self.close_event = close_event

        # Load the SLU.
        self.slu = slu_factory(cfg)

    def process_pending_commands(self):
        """
        Process all pending commands.

        Available commands:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.

        Return True if the process should terminate.
        """

        while self.commands.poll():
            command = self.commands.recv()
            if self.cfg['NLG']['debug']:
                self.cfg['Logging']['system_logger'].debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    return True

                if command.parsed['__name__'] == 'flush':
                    # Discard all data in input buffers.
                    while self.asr_hypotheses_in.poll():
                        self.asr_hypotheses_in.recv()

                    # the SLU components does not have to be flushed
                    # self.slu.flush()

                    self.commands.send(Command("flushed()", 'SLU', 'HUB'))

                    return False

        return False

    def read_asr_hypotheses_write_slu_hypotheses(self):
        if self.asr_hypotheses_in.poll():
            data_asr = self.asr_hypotheses_in.recv()

            if isinstance(data_asr, ASRHyp):
                slu_hyp = self.slu.parse(data_asr.hyp)
                fname = data_asr.fname

                confnet = None
                nblist = None

                if isinstance(slu_hyp, DialogueActConfusionNetwork):
                    confnet = slu_hyp
                    nblist = slu_hyp.get_da_nblist()
                elif isinstance(slu_hyp, DialogueActNBList):
                    confnet = None
                    nblist = slu_hyp


                if self.cfg['SLU']['debug']:
                    s = []
                    s.append("SLU Hypothesis")
                    s.append("-" * 60)
                    s.append("Confnet:")
                    s.append(unicode(confnet))
                    s.append("Nblist:")
                    s.append(unicode(nblist))
                    s.append("")
                    s = '\n'.join(s)
                    self.cfg['Logging']['system_logger'].debug(s)

                self.cfg['Logging']['session_logger'].slu("user", fname, nblist, confnet=confnet)

                self.commands.send(Command('slu_parsed(fname="%s")' % fname, 'SLU', 'HUB'))
                self.slu_hypotheses_out.send(SLUHyp(slu_hyp, asr_hyp=data_asr.hyp))

            elif isinstance(data_asr, Command):
                self.cfg['Logging']['system_logger'].info(data_asr)
            else:
                raise SLUException('Unsupported input.')

    def run(self):
        try:
            set_proc_name("Alex_SLU")

            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    return

                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                # process all pending commands
                if self.process_pending_commands():
                    return

                # process the incoming ASR hypotheses
                self.read_asr_hypotheses_write_slu_hypotheses()
        except:
            self.cfg['Logging']['system_logger'].exception(
                'Uncaught exception in SLU process.')
            self.close_event.set()
            raise
