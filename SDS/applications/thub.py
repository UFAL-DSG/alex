#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

import __init__

from SDS.components.hub import Hub
from SDS.components.asr.utterance import Utterance, UtteranceNBList
from SDS.components.slu import CategoryLabelDatabase, SLUPreprocessing
from SDS.components.slu.da import *
from SDS.components.slu.dailrclassifier import DAILogRegClassifier
from SDS.components.dm.dummydialoguemanager import DummyDM
from SDS.components.nlg.template import TemplateNLG
from SDS.utils.config import Config
from SDS.utils.exception import UtteranceException, TextHubException

class TextHub(Hub):
    """
      TextHub builds a text based testing environment for SLU, DM, and NLG components.
      It reads the text from the standard input and passes it into SLU. Then the dialogue acts
      are processed by a dialogue manager. The output of the dialogue manager in the form of
      dialogue acts is then converted by a NLG component into text, which is presented
      to the user.
    """
    def __init__(self, cfg):
        self.cfg = cfg

        self.slu = None
        self.dm = None
        self.nlg = None

        self.cldb = CategoryLabelDatabase(self.cfg['SLU']['cldb'])
        self.preprocessing = SLUPreprocessing(self.cldb)

        if self.cfg['SLU']['type'] == 'DAILogRegClassifier':
            self.slu = DAILogRegClassifier(self.preprocessing)
            self.slu.load_model(self.cfg['SLU']['DAILogRegClassifier']['model'])
        else:
            raise TextHubEception('Unsupported spoken language understanding: %s' % self.cfg['SLU']['type'])

        if self.cfg['DM']['type'] == 'Dummy':
            self.dm = DummyDM(cfg)
        else:
            raise TextHubEception('Unsupported dialogue manager: %s' % self.cfg['DM']['type'])

        if self.cfg['NLG']['type'] == 'Template':
            self.nlg = TemplateNLG(cfg)
        else:
            raise TextHubEception('Unsupported natural language generation: %s' % self.cfg['NLG']['type'])

    def parse_input_utt(self, l):
        """Converts a text including a dialogue act and its probability into a dialogue act instance and float probability.

        The input text must have the following form:
            [prob] this is a text input
        """
        ri = l.find(" ")

        prob = 1.0

        if ri != -1:
            utt = l[ri + 1:]

            try:
                prob = float(l[:ri])
            except:
                # I cannot convert the first part of the input as a float
                # Therefore, assume that all the input is a DA
                utt = l
        else:
            utt = l

        try:
            utt = Utterance(utt)
        except UtteranceException:
            raise TextHubEception("Invalid utterance: %s" % utt)

        return prob, utt

    def output_sys_da(self, da):
        """Prints the system dialogue act to the output."""
        print "System DA:", da
        print

    def output_sys_utt(self, utt):
        """Prints the system utterance to the output."""
        print "System:   ", utt
        print

    def output_usr_utt_nblist(self, utt_nblist):
        """Print the user input N-best list."""
        print "User utterance NBList:"
        print utt_nblist
        print

    def output_usr_da(self, das):
        """Print the user input dialogue acts."""
        if isinstance(das, DialogueActConfusionNetwork):
            print "User DA confusion network:"
            print das
            print
            print "User best DA hypothesis:"
            print das.get_best_da_hyp()
        else:
            print "User DA:"
            print das
            print



    def input_usr_utt_nblist(self):
        """Reads an N-best list of utterances from the input. """
        nblist = UtteranceNBList()
        i = 1
        while i < 100:
            l = raw_input("User %d:    " % i)
            if l.startswith("."):
                print
                break

            try:
                prob, da = self.parse_input_utt(l)
            except TextHubException as e:
                print e
                continue

            nblist.add(prob, da)

            i += 1

        nblist.merge()
        nblist.scale()
        nblist.normalise()
        nblist.sort()

        return nblist

    def run(self):
        """Controls the dialogue manager."""
        cfg['Logging']['system_logger'].info("""Enter the first user utterance. You can enter multiple utterances to form an N-best list.
        The probability for each utterance must be provided before the utterance itself. When finished, the entry
        can be terminated by a period ".".

        For example:

          System DA 1: 0.6 Hello
          System DA 2: 0.4 Hello, I am looking for a bar
          System DA 3: .
        """)

        while True:
            # new turn
            print "="*120
            print
            sys_da = self.dm.da_out()
            self.output_sys_da(sys_da)

            sys_utt = self.nlg.generate(sys_da)
            self.output_sys_utt(sys_utt)

            print '-'*120
            print

            utt_nblist = self.input_usr_utt_nblist()
            #self.output_usr_utt_nblist(utt_nblist)
            das = self.slu.parse(utt_nblist)
            self.output_usr_da(das)

            print '-'*120
            print
            self.dm.da_in(das)


#########################################################################
#########################################################################

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        TextHub builds a text based testing environment for SLU, DM, and NLG components.

        It reads the text from the standard input and passes it into SLU. Then the dialogue acts
        are processed by a dialogue manager. The output of the dialogue manager in the form of
        dialogue acts is then converted by a NLG component into text, which is presented
        to the user.

        The program reads the default config in the resources directory ('../resources/default.cfg') config
        in the current directory.

        In addition, it reads all config file passed as an argument of a '-c'.
        The additional config files overwrites any default or previous values.

      """)

    parser.add_argument(
        '-c', action="store", dest="configs", default=None, nargs='+',
        help='additional configure file')
    args = parser.parse_args()

    cfg = Config('../../resources/default.cfg')

    if args.configs:
        for c in args.configs:
            cfg.merge(c)
    cfg['Logging']['system_logger'].info('config = ' + str(cfg))

    #########################################################################
    #########################################################################
    cfg['Logging']['system_logger'].info("Sem Hub\n" + "=" * 120)

    shub = TextHub(cfg)

    shub.run()
