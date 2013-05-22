#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import time

import alex.components.slu.dailrclassifier as DAILRSLU
import alex.components.slu.daiklrclassifier as DAIKLRSLU
import alex.components.slu.templateclassifier as TSLU

from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import DialogueActConfusionNetwork
from alex.components.hub.messages import Command, ASRHyp, SLUHyp
from alex.utils.exception import DMException

class SLU(multiprocessing.Process):
    """The SLU component receives an ASR hypotheses and converts them into hypotheses about the meaning
    of the input in the form of dialogue acts.

    This component is a wrapper around multiple SLU components which handles multiprocessing
    communication.
    """

    def __init__(self, cfg, commands, asr_hypotheses_in, slu_hypotheses_out):
        multiprocessing.Process.__init__(self)

        self.cfg = cfg

        self.commands = commands
        self.asr_hypotheses_in = asr_hypotheses_in
        self.slu_hypotheses_out = slu_hypotheses_out

        self.cldb = CategoryLabelDatabase(self.cfg['SLU']['cldb'])
        preprocessing_cls = self.cfg['SLU'].get('preprocessing_cls', SLUPreprocessing)

        self.preprocessing = preprocessing_cls(self.cldb)

        self.slu = None
        if self.cfg['SLU']['type'] == 'Template':
            self.slu = TNLG.TemplateClassifier(cfg)
        elif self.cfg['SLU']['type'] == 'DAILogRegClassifier':
            # FIXME: maybe the SLU components should use the Config class to initialise themselves.
            # As a result it would created their category label database and pre-processing classes.

            self.slu = DAILRSLU.DAILogRegClassifier(self.preprocessing)
            self.slu.load_model(self.cfg['SLU']['DAILogRegClassifier']['model'])
        elif self.cfg['SLU']['type'] == 'DAIKerLogRegClassifier':
            self.slu = DAILRSLU.DAIKerLogRegClassifier(self.preprocessing)
            self.slu.load_model(self.cfg['SLU']['DAIKerLogRegClassifier']['model'])
        else:
            raise VoipHubException('Unsupported SLU component: %s' % self.cfg['NLG']['type'])

    def process_pending_commands(self):
        """Process all pending commands.

        Available commands:
          stop() - stop processing and exit the process
          flush() - flush input buffers.
            Now it only flushes the input connection.

        Return True if the process should terminate.
        """

        if self.commands.poll():
            command = self.commands.recv()
            if self.cfg['NLG']['debug']:
                self.cfg['Logging']['system_logger'].debug(command)

            if isinstance(command, Command):
                if command.parsed['__name__'] == 'stop':
                    return True

                if command.parsed['__name__'] == 'flush':
                    # discard all data in in input buffers
                    while self.asr_hypotheses_in.poll():
                        data_in = self.asr_hypotheses_in.recv()

                    # the SLU components does not have to be flused
                    #self.slu.flush()

                    return False

        return False

    def read_asr_hypotheses_write_slu_hypotheses(self):
        while self.asr_hypotheses_in.poll():
            data_asr = self.asr_hypotheses_in.recv()

            if isinstance(data_asr, ASRHyp):
                slu_hyp = self.slu.parse(data_asr.hyp)

                if self.cfg['SLU']['debug']:
                    s = []
                    s.append("SLU Hypothesis")
                    s.append("-"*60)
                    s.append(str(slu_hyp))
                    s.append("")
                    s = '\n'.join(s)
                    self.cfg['Logging']['system_logger'].debug(s)

                if type(slu_hyp) is DialogueActConfusionNetwork:
                    confnet = slu_hyp
                else:
                    confnet = None

                # TODO HACK
                #self.cfg['Logging']['session_logger'].slu("user", slu_hyp.get_da_nblist(), confnet=confnet)

                self.commands.send(Command('slu_parsed()', 'SLU', 'HUB'))
                self.slu_hypotheses_out.send(SLUHyp(slu_hyp))

            elif isinstance(data_asr, Command):
                self.cfg['Logging']['system_logger'].info(data_asr)
            else:
                raise DMException('Unsupported input.')

    def run(self):
        self.recognition_on = False

        while 1:
            time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

            # process all pending commands
            if self.process_pending_commands():
                return

            # process the incoming ASR hypotheses
            self.read_asr_hypotheses_write_slu_hypotheses()
