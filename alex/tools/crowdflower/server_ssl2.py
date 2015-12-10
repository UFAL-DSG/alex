#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
server_ssl2.py
==============

A HTTPS server to help with PTIEN jobs at CrowdFlower. Serves
different tasks for the users and handles code verification.

The default is to use files `server.crt` and `server.key` located in the same directory as
the SSL key and certificate. The default is to listen on port 443. These defaults may be
overridden (see usage).

The default paths to code storage, log file, and tasks storage are `./codes`, `./log`,
and `./tasks`, respectively.

By default, codes never expire. This can be changed using the `--timeout` parameter.

The API
-------
- it accepts three query parameters: a,q and r
- it returns simple JSON with one node "response" [yes,no,success,online]
- if a is "1" (?q=CODE&a=1), then CODE is added and the response is "success"
    - NB: if the code is already in the database, the response is "failure"
- if r is "1" (?q=CODE&r=1), then CODE is removed and the response is "success"
- if CODE is present in "code_path" file it returns "yes" otherwise "no"
- if CODE is equal to "test" it sends "online" in response - connection check
- if CODE is equal to "task", a random HTML representation of a task is returned

Usage
-----

./server_ssl2.py [--port XXXX] [--key path/to/file.key] [--cert path/to/file.crt] \
        [--codes path/to/code/storage.tsv] [--log path/to/logfile] [--timeout <minutes>] \
        [--tasks path/to/tasks/file]
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


DEFAULT_PORT = 443
DEFAULT_CODES_PATH = "./codes"
DEFAULT_LOG_PATH = "./log"
DEFAULT_TASKS_PATH = "./tasks"
MYDIR = os.path.dirname(__file__)
DEFAULT_KEY_PATH = os.path.join(MYDIR, 'server.key')
DEFAULT_CERT_PATH = os.path.join(MYDIR, 'server.crt')
DEFAULT_TIMEOUT = -1


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        """Main method that handles a GET request from the client."""
        response = ""
        try:
            self.server.log(str(self.path))

            query = urlparse(self.path).query

            query_components = dict(qc.split("=") for qc in query.split("&"))
            query_code = query_components["q"]

            add = query_components.get('a')
            remove = query_components.get('r')
            # callback = query_components["callback"] if query_components.has_key("callback") else ""

            # connection test
            if query_code == "test":
                response = "online"

            # get a random task
            elif query_code == "task":
                response = self.server.get_random_task()

            # try to add code to database
            elif add == "1":
                if self.server.add_code(query_code):
                    response = "success"
                else:
                    response = "failure"

            # remove code from database
            elif remove == "1":
                self.server.remove_code(query_code)
                response = "success"

            # check validity of code, remove it if successful
            else:
                codes = self.server.read_codes()
                if query_code in codes:
                    self.server.remove_code(query_code)
                    response = 'yes'
                else:
                    response = 'no'

        except Exception as e:
            print >> sys.stderr, unicode(e).encode('utf-8')
            response = "no"
            # callback = ""

        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # for jsonp calls
        # if callback:
        #     self.wfile.write( callback + '(' + json.dumps({'response':response}) + ')' )
        #     self.request.sendall( callback + '(' + json.dumps({'response':response}) + ')')
        # else:
        self.wfile.write(json.dumps({'response': response}))
        # self.request.sendall(json.dumps({'response':response}))


class SSLTCPServer(SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass, settings, bind_and_activate=True):
        """Constructor. May be extended, do not override."""

        self.task_path = settings['tasks']
        self.log_path = settings['log']
        self.code_path = settings['codes']
        self.key_file = settings['key']
        self.cert_file = settings['cert']
        self.timeout = settings['timeout']

        # read the tasks and store them for reuse
        self.tasks = self.read_tasks(self.task_path)
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

    def read_tasks(self, path):
        """Read the tasks from format produced by generate_tasks.py (1-line DAs, 1-line sentences,
        followed by empty line). The individual DAs and sentences are separated with tab characters.

        @param path: The file to read.
        """
        buf = []
        das = None
        sents = None

        with codecs.open(path, "r", 'UTF-8') as fh_in:
            for line in fh_in:
                line = line.strip()
                if not line:
                    buf.append((das, sents))
                    das = None
                    sents = None
                if not das:
                    das = line
                elif not sents:
                    sents = line
        return buf

    def get_random_task(self):
        """Return a HMTL representation for a random task (out of tasks stored in `self.task`)."""
        _, sents = random.choice(self.tasks)
        text = '<ol>\n'
        for sent in sents.split('\t'):
            text += '<li>' + sent + '</li>\n'
        text += '</ol>\n'
        return text

    def read_codes(self):
        data = {}
        if not os.path.isfile(self.code_path):
            return data
        dt_now = int(time.time())
        with codecs.open(self.code_path, 'r', 'UTF-8') as fh_in:
            for line in fh_in:
                line = line.strip()
                if not line:  # skip empty lines
                    continue
                cur_code, cur_dt = line.strip().split('\t')
                dt_code = int(cur_dt)
                if self.timeout > 0 and dt_code + self.timeout * 60 < dt_now:  # skip old codes
                    continue
                # remember the valid code
                data[cur_code] = cur_dt
        return data

    def remove_code(self, code_to_remove):
        data = self.read_codes()
        with codecs.open(self.code_path, "w", 'UTF-8') as fh_out:
            for code, timestamp in data.iteritems():
                if code != code_to_remove:
                    print >> fh_out, code + "\t" + str(timestamp)

    def add_code(self, code_to_add):
        data = self.read_codes()
        if code_to_add in data:
            return False
        data[code_to_add] = int(time.time())
        with codecs.open(self.code_path, "w", 'UTF-8') as fh_out:
            for code, timestamp in data.iteritems():
                print >> fh_out, code + "\t" + str(timestamp)
        return True

    def log(self, request):
        with codecs.open(self.log_path, "a", 'UTF-8') as fh_out:
            print >> fh_out, request


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
    ap.add_argument('--tasks', default=DEFAULT_TASKS_PATH)
    ap.add_argument('-l', '--log', default=DEFAULT_LOG_PATH)
    ap.add_argument('-t', '--timeout', type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument('--codes', default=DEFAULT_CODES_PATH)
    args = ap.parse_args()
    run(settings=vars(args))
