#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.

import autopath

import argparse

from alex.components.asr.utterance import Utterance, UtteranceNBList, \
    UtteranceException
from alex.components.dm.common import dm_factory, get_dm_type
from alex.components.hub import Hub
from alex.components.slu.base import CategoryLabelDatabase, SLUPreprocessing
from alex.components.slu.da import DialogueActConfusionNetwork
from alex.components.slu.common import slu_factory, get_slu_type
from alex.components.slu.dailrclassifier import DAILogRegClassifier
from alex.components.nlg.common import nlg_factory, get_nlg_type
from alex.utils.config import Config
from alex.utils.ui import getTerminalSize
from alex.utils.config import as_project_path


class TextHub(Hub):
    """\
      Provides a natural text interface to the dialogue system.

      TextHub builds a text based testing environment for SLU, DM, and NLG
      components.  It reads the text from the standard input and passes it on
      to SLU. Then the dialogue acts are processed by a dialogue manager. The
      output of the dialogue manager in the form of dialogue acts is then
      converted by a NLG component into text, which is presented to the user.

    """
    hub_type = "THub"

    def __init__(self, cfg):
        super(TextHub, self).__init__(cfg)

        self.slu = None
        self.dm = None
        self.nlg = None

        slu_type = get_slu_type(cfg)
        self.slu = slu_factory(slu_type, cfg)

        dm_type = get_dm_type(cfg)
        self.dm = dm_factory(dm_type, cfg)
        self.dm.new_dialogue()

        nlg_type = get_nlg_type(cfg)
        self.nlg = nlg_factory(nlg_type, cfg)

    def parse_input_utt(self, l):
        """Converts a text including a dialogue act and its probability into
        a dialogue act instance and float probability.

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
        print "System DA:", unicode(da)
        print

    def output_sys_utt(self, utt):
        """Prints the system utterance to the output."""
        print "System:   ", utt
        print

    def output_usr_utt_nblist(self, utt_nblist):
        """Print the user input N-best list."""
        print "User utterance NBList:"
        print unicode(utt_nblist)
        print

    def output_usr_da(self, das):
        """Print the user input dialogue acts."""
        if isinstance(das, DialogueActConfusionNetwork):
            print "User DA confusion network:"
            print unicode(das)
            print
            print "User best DA hypothesis:"
            print unicode(das.get_best_da_hyp())
        else:
            print "User DA:"
            print unicode(das)
            print

    def input_usr_utt_nblist(self):
        """Reads an N-best list of utterances from the input. """

        self.init_readline()

        nblist = UtteranceNBList()
        i = 1
        while i < 100:
            l = raw_input("User %d:    " % i).decode('utf8')
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
        nblist.add_other()

        self.write_readline()

        return nblist

    def process_dm(self):
        # new turn
        term_width = getTerminalSize()[1] or 120
        print "=" * term_width
        print
        sys_da = self.dm.da_out()
        self.output_sys_da(sys_da)

        #import ipdb; ipdb.set_trace()

        sys_utt = self.nlg.generate(sys_da)
        self.output_sys_utt(sys_utt)

        term_width = getTerminalSize()[1] or 120
        print '-' * term_width
        print


    def process_utterance_hyp(self, utterance_hyp):
        #self.output_usr_utt_nblist(utt_nblist)
        das = self.slu.parse(utterance_hyp)
        self.output_usr_da(das)

        term_width = getTerminalSize()[1] or 120
        print '-' * term_width
        print
        self.dm.da_in(das, utterance_hyp)
        #self.dm.da_in(das)

    def run(self):
        """Controls the dialogue manager."""
        cfg['Logging']['system_logger'].info(
            """Enter the first user utterance.  You can enter multiple
            utterances to form an N-best list.  The probability for each
            utterance must be provided before the utterance itself.  When
            finished, the entry can be terminated by a period (".").

            For example:

            System DA 1: 0.6 Hello
            System DA 2: 0.4 Hello, I am looking for a bar
            System DA 3: .
        """)

        while True:
            self.process_dm()
            utt_nblist = self.input_usr_utt_nblist()
            self.process_utterance_hyp(utt_nblist)



#########################################################################
#########################################################################

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        TextHub builds a text based testing environment for SLU, DM, and NLG
        components.

        It reads the text from the standard input and passes it into SLU. Then
        the dialogue acts are processed by a dialogue manager. The output of
        the dialogue manager in the form of dialogue acts is then converted by
        a NLG component into text, which is presented to the user.

        The program reads the default config in the resources directory
        ('../resources/default.cfg') config in the current directory.

        In addition, it reads all config file passed as an argument of a '-c'.
        The additional config files overwrites any default or previous values.

      """)

    parser.add_argument(
        '-c', action="append", dest="configs", default=None,
        help='additional configure file')
    parser.add_argument(
        '-s', action="append", dest="scripts", default=None,
        help='automated scripts')
    args = parser.parse_args()

    cfg = Config(as_project_path('resources/default.cfg'))

    if args.configs:
        for c in args.configs:
            cfg.merge(c)
    cfg['Logging']['system_logger'].info('config = ' + str(cfg))

    #########################################################################
    #########################################################################
    term_width = getTerminalSize()[1] or 120
    cfg['Logging']['system_logger'].info("Text Hub\n" + "=" * (term_width - 4))

    shub = TextHub(cfg)

    if args.scripts:
        for script in args.scripts:
            with open(script) as f_in:
                for ln in f_in:
                    shub.process_dm()
                    ln = ln.decode('utf8').strip()
                    print "SCRIPT: %s" % ln
                    shub.process_utterance_hyp(Utterance(ln))


    shub.run()
