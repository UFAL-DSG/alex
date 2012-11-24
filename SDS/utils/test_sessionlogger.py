#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

import autopath

from SDS.utils.config import Config
from SDS.utils.sessionlogger import SessionLogger, SessionLoggerException


class TestSessionLogger(unittest.TestCase):
    def test_session_logger(self):
        cfg = Config('resources/default.cfg', project_root=True)
        
        sl = SessionLogger()
        
        sl.session_start('./')
        sl.config('config = ' + str(cfg))
        sl.header(cfg['Logging']["system_name"], cfg['Logging']["version"])
        sl.input_source("voip")
        
        sl.turn("system")
        sl.dialogue_act("system", "hello()")
        sl.text("system", "Hello.")
        sl.rec_start("system", "system.wav")
        sl.rec_end("system.wav")
            
        sl.turn("user")
        sl.rec_start("user", "user.wav")
        sl.rec_end("user.wav")
            
if __name__ == '__main__':
    unittest.main()
