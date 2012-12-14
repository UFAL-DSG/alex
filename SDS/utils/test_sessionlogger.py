#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os

if __name__ == "__main__":
    import autopath

from SDS.components.asr.utterance import UtteranceConfusionNetwork
from SDS.components.slu.da import DialogueAct, DialogueActItem, DialogueActConfusionNetwork
from SDS.utils.config import Config
from SDS.utils.sessionlogger import SessionLogger, SessionLoggerException

class TestSessionLogger(unittest.TestCase):
    def test_session_logger(self):
        cfg = Config('resources/default.cfg', project_root=True)

        sl = SessionLogger()

        # test 3 calls at once
        for i in range(3):
            sess_dir = "./%d" % i
            if not os.path.isdir(sess_dir):
                os.mkdir(sess_dir)
            sl.session_start(sess_dir)
            sl.config('config = ' + str(cfg))
            sl.header(cfg['Logging']["system_name"], cfg['Logging']["version"])
            sl.input_source("voip")

            sl.dialogue_rec_start(None, "both_complete_dialogue.wav")
            sl.dialogue_rec_start("system", "system_complete_dialogue.wav")
            sl.dialogue_rec_start("user", "user_complete_dialogue.wav")
            sl.dialogue_rec_end("both_complete_dialogue.wav")
            sl.dialogue_rec_end("system_complete_dialogue.wav")
            sl.dialogue_rec_end("user_complete_dialogue.wav")

            sl.turn("system")
            sl.dialogue_act("system", "hello()")
            sl.text("system", "Hello.")
            sl.rec_start("system", "system1.wav")
            sl.rec_end("system1.wav")

            sl.turn("user")
            sl.rec_start("user", "user1.wav")
            sl.rec_end("user1.wav")

            A1, A2, A3 = 0.90, 0.05, 0.05
            B1, B2, B3 = 0.70, 0.20, 0.10
            C1, C2, C3 = 0.80, 0.10, 0.10

            asr_confnet = UtteranceConfusionNetwork()
            asr_confnet.add([[A1, "want"], [A2, "has"], [A3, 'ehm']])
            asr_confnet.add([[B1, "Chinese"],  [B2, "English"], [B3, 'cheap']])
            asr_confnet.add([[C1, "restaurant"],  [C2, "pub"],   [C3, 'hotel']])
            asr_confnet.merge()
            asr_confnet.normalise()
            asr_confnet.sort()

            asr_nblist = asr_confnet.get_utterance_nblist()

            sl.asr("user", asr_nblist, asr_confnet)

            slu_confnet = DialogueActConfusionNetwork()
            slu_confnet.add(0.7, DialogueActItem('hello'))
            slu_confnet.add(0.6, DialogueActItem('thankyou'))
            slu_confnet.add(0.4, DialogueActItem('restart'))
            slu_confnet.add(0.1, DialogueActItem('bye'))
            slu_confnet.merge()
            slu_confnet.normalise()
            slu_confnet.sort()

            slu_nblist = slu_confnet.get_da_nblist()

            sl.slu("user", slu_nblist, slu_confnet)

            sl.turn("system")
            sl.dialogue_act("system", "thankyou()")
            sl.text("system", "Thank you.", cost = 1.0)
            sl.rec_start("system", "system2.wav")
            sl.rec_end("system2.wav")
            sl.barge_in("system", tts_time = True)

            sl.turn("user")
            sl.rec_start("user", "user2.wav")
            sl.rec_end("user2.wav")
            sl.hangup("user")

if __name__ == '__main__':
    unittest.main()
