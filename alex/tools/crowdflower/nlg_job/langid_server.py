#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TODO Merge identical code with server_ssl2.py

'''
langid_server.py
==============

A HTTPS server to help with PTIEN NLG jobs at CrowdFlower. Handles fluency assessment
(currently only implemented as language detection + spell checking).

The default is to use files `server.crt` and `server.key` located in the same directory as
the SSL key and certificate. The default is to listen on port 443. These defaults may be
overridden (see usage).

The API
-------

### Requests

The server accepts the query parameters: *rd*, *ut*

Parameter *rd* (requested data):

- Just provide the DAIs that the user was supposed to describe (currently not used in any way).

Parameter *ut* (user text):

- Provide the user-entered text for assessment.

### Response shape

The response is always a JSON dictionary. It always contains at two keys, `'result'`
and `'text'` (the first is a binary `yes`/`no`, the second just copies the input text).


Usage
-----

./server_ssl2.py [--port XXXX] [--key path/to/file.key] [--cert path/to/file.crt] \
        [--codes path/to/code/storage.tsv] [--log path/to/logfile] [--timeout <minutes>] \
        [--tasks path/to/tasks/file] [--allow-ip 0.0.0.0-255.255.255.255]


Dependencies
------------

- langid (https://github.com/saffsd/langid.py)
- langdetect (https://pypi.python.org/pypi/langdetect)
- hunspell (https://pypi.python.org/pypi/hunspell)

'''

import codecs
import json
from BaseHTTPServer import BaseHTTPRequestHandler
from urlparse import urlparse
import os
import SocketServer
import argparse
import random
import time
import ssl
import sys
import langdetect
import langid
import urllib
import hunspell
import re

DEFAULT_PORT = 443
MYDIR = os.path.dirname(__file__)
DEFAULT_LOG_PATH = "./log"
DEFAULT_KEY_PATH = os.path.join(MYDIR, 'server.key')
DEFAULT_CERT_PATH = os.path.join(MYDIR, 'server.crt')
DEFAULT_ALLOW_IP = '0.0.0.0-255.255.255.255'


class IPRange(object):

    def __init__(self, range_str):
        """Initialize using a range string, such as 0.0.0.0-255.255.255.255."""
        self.lo, self.hi = (self._parse_addr(addr_str) for addr_str in range_str.split('-'))

    def _parse_addr(self, addr_str):
        """Parse an IP address to an integer representation for easy comparisons."""
        addr = [int(i) for i in addr_str.split('.')]
        if len(addr) != 4 or any([i < 0 for i in addr]) or any([i > 255 for i in addr]):
            raise ValueError('Invalid IP address: %s' % addr_str)
        val = 0
        for i in addr:
            val *= 255
            val += i
        return val

    def is_in_range(self, addr_str):
        """Return True if the given address (string) is in this range."""
        addr = self._parse_addr(addr_str)
        return self.lo <= addr and addr <= self.hi


class Handler(BaseHTTPRequestHandler):

    # set a timeout so that the server never hangs (this should be vastly more than enough
    # for handling a single request, with no file access blocking etc.)
    timeout = 30

    def do_GET(self):
        """Main method that handles a GET request from the client."""
        response = ""
        response_code = 200
        try:
            self.server.log(self.client_address, str(self.path))

            query = urlparse(self.path).query

            query_components = dict(qc.split("=") for qc in query.split("&"))
            user_text = urllib.unquote(query_components.get('ut', ''))
            request_data = urllib.unquote(query_components.get('rd', ''))

            # connection test
            if not user_text or not request_data:
                user_text = ''
                response = 'online'

            # fluency assessment
            else:
                l1 = langdetect.detect(user_text)
                l2, _ = langid.classify(user_text)
                good, tot = self.server.spellcheck(request_data.split(','), user_text)
                ban_phr = self.server.check_banned_phrases(user_text)
                # one of the detectors must say it's English, allow 1 typo per 10 words
                response = ('yes'
                            if ((l1 == 'en' or l2 == 'en') and (tot - good <= tot / 10 + 1) and not ban_phr)
                            else ('no:' + l1 + ' ' + l2 +
                                  (' spellcheck score: %d / %d' % (good, tot)) +
                                  ' ban_phr: ' + ban_phr))

        except Exception as e:
            print >> sys.stderr, unicode(e).encode('utf-8')
            import traceback
            traceback.print_exc()
            user_text = ''
            response = 'no'

        self.send_response(response_code)
        self.send_header("Access-Control-Allow-Origin", "*")  # CORS
        self.end_headers()

        ret = {'result': response, 'text': user_text}
        self.wfile.write(json.dumps(ret))


class SSLTCPServer(SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass, settings, bind_and_activate=True):
        """Constructor. May be extended, do not override."""

        self.log_path = settings['log']
        self.key_file = settings['key']
        self.cert_file = settings['cert']
        self.allow_ip = IPRange(settings['allow_ip'])

        self.spellchecker = hunspell.HunSpell('/usr/share/hunspell/en_US.dic',
                                              '/usr/share/hunspell/en_US.aff')

        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, False)

        # initialize SSL connection
        self.socket = ssl.wrap_socket(self.socket,
                                      keyfile=self.key_file,
                                      certfile=self.cert_file,
                                      cert_reqs=ssl.CERT_NONE,
                                      ssl_version=ssl.PROTOCOL_TLSv1,
                                      server_side=True)

        # start serving
        if bind_and_activate:
            self.server_bind()
            self.server_activate()

    def log(self, client_addr, request):
        """Log the request path and client address (IP + port), along with current time."""
        with codecs.open(self.log_path, "a", 'UTF-8') as fh_out:
            print >> fh_out, (time.strftime('%Y-%m-%d %H:%M:%S') + "\t" +
                              ':'.join([str(i) for i in client_addr]) + "\t" +
                              request)

    def is_addr_allowed(self, client_addr):
        """Return true if the given client address (IP + port) is allowed to add keys."""
        return self.allow_ip.is_in_range(client_addr[0])

    def spellcheck(self, data_items, text):
        """Run spellchecker."""

        data_toks = set()
        for data_item in data_items:
            data_toks.update(data_item.lower().split(' '))

        # tokenize
        toks = ' ' + text + ' '  # pad with spaces for easy regexes
        toks = re.sub(r'([?.!;,:-]+)', r' ', toks)
        toks = re.sub(r'\s+', ' ', toks)
        toks = toks[1:-1].split(' ')  # remove the padding spaces and split

        good_toks = 0
        for tok in toks:
            if tok.lower() in data_toks or self.spellchecker.spell(tok):
                good_toks += 1

        return good_toks, len(toks)

    def check_banned_phrases(self, text):
        """Check for various phrases that are not considered fluent."""
        if re.search(r'\bfrom +to +where\b', text, re.IGNORECASE):
            return 'from to where'
        if re.search(r'\bwhere +where\b', text, re.IGNORECASE):
            return 'where where'
        return ''


def run(server_class=SSLTCPServer, settings={}):

    httpd = server_class(('', settings['port']), Handler, settings, True)
    sa = httpd.socket.getsockname()

    print "Serving HTTPS on", sa[0], "port", sa[1], "..."
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
    print "Server Stopped - %s:%s" % (sa[0], sa[1])


if __name__ == '__main__':
    random.seed()
    ap = argparse.ArgumentParser()
    ap.add_argument('-p', '--port', type=int, default=DEFAULT_PORT)
    ap.add_argument('-c', '--cert', default=DEFAULT_CERT_PATH)
    ap.add_argument('-k', '--key', default=DEFAULT_KEY_PATH)
    ap.add_argument('-l', '--log', default=DEFAULT_LOG_PATH)
    ap.add_argument('-i', '--allow-ip', default=DEFAULT_ALLOW_IP)
    args = ap.parse_args()
    run(settings=vars(args))
