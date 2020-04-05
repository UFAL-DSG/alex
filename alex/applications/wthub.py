#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.

from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import argparse
import codecs
import json
import cgi

from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceException
from alex.components.dm.common import dm_factory, get_dm_type
from alex.utils.config import Config
from alex.applications.thub import TextHub


class WebTextHub(TextHub):
    """Text hub to work as web server."""

    hub_type = "THub"

    def __init__(self, cfg, tts_preproc_output=False):
        super(WebTextHub, self).__init__(cfg, tts_preproc_output)
        self.in_session = False

    def process_dm(self):
        # new turn
        self.cfg['Logging']['session_logger'].turn("system")
        self.dm.log_state()

        sys_da = self.dm.da_out()
        self.output_sys_da(sys_da)

        self.cfg['Logging']['session_logger'].dialogue_act("system", sys_da)

        sys_utt = self.nlg.generate(sys_da)
        self.output_sys_utt(sys_utt)
        self.cfg['Logging']['system_logger'].info('System: ' + unicode(sys_utt))

        return sys_utt

    def process_utterance_hyp(self, obs):
        das = self.slu.parse(obs)
        self.output_usr_da(das)

        self.cfg['Logging']['session_logger'].turn("user")
        self.cfg['Logging']['session_logger'].slu("user", "*", das)

        self.dm.da_in(das, obs.values()[0])

    def get_response(self, utt_text):
        try:
            self.cfg['Logging']['system_logger'].info('User: ' + unicode(utt_text))
            utt_nblist = UtteranceNBList()
            utt_nblist.add(1.0, Utterance(utt_text))
            self.process_utterance_hyp({'utt_nbl': utt_nblist})
            return self.process_dm()

        except Exception:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in WTHUB process.')
            return None

    def start_session(self):

        if self.in_session:
            self.end_session()

        self.in_session = True
        self.cfg['Logging']['system_logger'].session_start("localhost-" + unicode(args.port))
        self.cfg['Logging']['system_logger'].session_system_log('config = ' + unicode(cfg))

        self.cfg['Logging']['session_logger'].session_start(cfg['Logging']['system_logger'].get_session_dir_name())
        self.cfg['Logging']['session_logger'].config('config = ' + unicode(cfg))
        self.cfg['Logging']['session_logger'].header(cfg['Logging']["system_name"], cfg['Logging']["version"])
        self.cfg['Logging']['session_logger'].input_source("text")

        try:
            self.dm.new_dialogue()
            return self.process_dm()  # welcome message
        except Exception:
            self.cfg['Logging']['system_logger'].exception('Uncaught exception in WTHUB process.')
            return None

    def end_session(self):

        self.cfg['Logging']['system_logger'].session_end()
        self.cfg['Logging']['session_logger'].session_end()
        self.in_session = False

class WTHHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        # from https://gist.github.com/nitaku/10d0662536f37a087e1b
        # refuse to receive non-json content
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        if ctype != 'application/json':
            self.send_response(400)
            self.end_headers()
            return
        # read the message and convert it into a python dictionary
        length = int(self.headers.getheader('content-length'))
        message = json.loads(self.rfile.read(length), encoding='UTF-8')

        print('PROCESSING MESSAGE: ' + unicode(message))
        if message.get('start_session'):
            sys_response = self.server.wthub.start_session()
        elif message.get('end_session'):
            self.server.wthub.end_session()
            sys_response = '[STOP]'
        else:
            if not self.server.wthub.in_session:
                self.server.wthub.start_session()
            sys_response = self.server.wthub.get_response(message['user'])

        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({'system': sys_response}, ensure_ascii=False).encode('UTF-8'))


class WTHServer(HTTPServer):

    def __init__(self, server_address, wthub):
        HTTPServer.__init__(self, server_address, WTHHandler)
        self.wthub = wthub




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

    parser.add_argument('-c', '--configs', nargs='+',
                        help='additional configuration files')
    parser.add_argument('-s', action="append", dest="scripts", default=None,
                        help='automated scripts')
    parser.add_argument('-t', '--tts-preprocessing', '--tts', dest='tts_preprocessing',
                        action='store_true', help='output TTS preprocessing results')
    parser.add_argument('-p', '--port', help='Port to serve on', default=8123, type=int)
    args = parser.parse_args()

    cfg = Config.load_configs(args.configs)

    #########################################################################
    #########################################################################
    cfg['Logging']['system_logger'].info("Text Hub\n" + "=" * 60)

    wthub = WebTextHub(cfg, args.tts_preprocessing)
    wthserver = WTHServer(('localhost', args.port), wthub)
    wthserver.serve_forever()
