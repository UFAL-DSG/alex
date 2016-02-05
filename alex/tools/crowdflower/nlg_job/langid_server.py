#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
server_ssl2.py
==============

A HTTPS server to help with PTIEN jobs at CrowdFlower. Serves
tasks assignments for the users and handles code verification.

The default is to use files `server.crt` and `server.key` located in the same directory as
the SSL key and certificate. The default is to listen on port 443. These defaults may be
overridden (see usage).

The default paths to code storage, log file, and tasks storage are `./codes`, `./log`,
and `./tasks`, respectively.

By default, codes never expire. This can be changed using the `--timeout` parameter.

The API
-------

### Requests

The server accepts the query parameters: *a*, *q*, *d*, *r*.

Parameter *q* (query/code):

- if CODE is a four-digit number present in the code storage, it returns "yes", otherwise "no"
    - additionally, if a call log directory has been sent using the *d* parameter,
      it is also returned.
- if CODE is equal to "test", it sends "online" in response - connection check
- if CODE is equal to "task", a random HTML representation of a task is returned

Parameter *a* (add, only used with *q*):

- if a is "1" (?q=CODE&a=1), then CODE is added and the response is "success"
    - NB: if the code is already in the database, the response is "failure"
    - if the --allow-ip command-line setting is used, using this parameter is only allowed
      to the given range of IP addresses (otherwise, the code is not added and the response
      is "unauthorized").

Parameter *d* (directory, only used with *q* and *a*):

- this optionally specifies a call log directory for the given code which will be returned
  on successfully checking the code using *q*.

Parameter *r* (remove, only used with *q*):

- if r is "1" (?q=CODE&r=1), then CODE is removed and the response is "success"


### Response shape

The response is always a JSON dictionary. It always contains at least one key, `'response'`.
For some queries, an additional key, `'data'`, may be present.

For a `q=test` request, the `response` is `online`.

If a task is requested using `q=task`, the `response` key contains a textual description
of the task, while the `data` key contains the corresponding dialogue acts.

If a code is added or removed from the database, the `response` is `success` or `failure`
(`failure` only when trying to add a code that is already in the database).

If a code is checked, the `response` is `no` for an unsuccessful and `yes` for a successful
check. If the server has been provided with a call log directory upon adding the code in
the database, the `data` contains the directory.


Usage
-----

./server_ssl2.py [--port XXXX] [--key path/to/file.key] [--cert path/to/file.crt] \
        [--codes path/to/code/storage.tsv] [--log path/to/logfile] [--timeout <minutes>] \
        [--tasks path/to/tasks/file] [--allow-ip 0.0.0.0-255.255.255.255]
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
        data = ""
        response_code = 200
        try:
            self.server.log(self.client_address, str(self.path))

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
                response, data = self.server.get_random_task()

            # try to add code to database (optionally with a call log directory)
            elif add == "1":
                if not self.server.is_addr_allowed(self.client_address):
                    response_code = 401
                    response = "unauthorized"
                elif self.server.add_code(query_code, query_components.get('d', '')):
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
                    _, data = codes[query_code]
                    self.server.remove_code(query_code)
                    response = 'yes'
                else:
                    response = 'no'

        except Exception as e:
            print >> sys.stderr, unicode(e).encode('utf-8')
            # import traceback
            # traceback.print_exc()
            response = "no"
            # callback = ""

        self.send_response(response_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # for jsonp calls
        # if callback:
        #     self.wfile.write( callback + '(' + json.dumps({'response':response}) + ')' )
        #     self.request.sendall( callback + '(' + json.dumps({'response':response}) + ')')
        # else:
        ret = {'response': response}
        if data:
            ret['data'] = data
        self.wfile.write(json.dumps(ret))
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
        self.allow_ip = IPRange(settings['allow_ip'])

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
        das, sents = random.choice(self.tasks)
        text = ''
        for sent in sents.split('\t'):
            text += '<p>' + sent + '</p>\n'
        return text, das

    def read_codes(self):
        data = {}
        if not os.path.isfile(self.code_path):
            return data
        dt_now = int(time.time())
        with codecs.open(self.code_path, 'r', 'UTF-8') as fh_in:
            for line in fh_in:
                line = line.strip("\r\n")
                if not line:  # skip empty lines
                    continue
                cur_code, cur_dt, cur_dir = line.split('\t')
                dt_code = int(cur_dt)
                if self.timeout > 0 and dt_code + self.timeout * 60 < dt_now:  # skip old codes
                    continue
                # remember the valid code
                data[cur_code] = (cur_dt, cur_dir)
        return data

    def remove_code(self, code_to_remove):
        data = self.read_codes()
        with codecs.open(self.code_path, "w", 'UTF-8') as fh_out:
            for code, (timestamp, logdir) in data.iteritems():
                if code != code_to_remove:
                    print >> fh_out, code + "\t" + str(timestamp) + "\t" + logdir

    def add_code(self, code_to_add, dir_to_add=''):
        """Add a code to the database, optionally with a call log directory path."""
        data = self.read_codes()
        if code_to_add in data:
            return False
        data[code_to_add] = (int(time.time()), dir_to_add)
        with codecs.open(self.code_path, "w", 'UTF-8') as fh_out:
            for code, (timestamp, logdir) in data.iteritems():
                print >> fh_out, code + "\t" + str(timestamp) + "\t" + logdir
        return True

    def log(self, client_addr, request):
        """Log the request path and client address (IP + port), along with current time."""
        with codecs.open(self.log_path, "a", 'UTF-8') as fh_out:
            print >> fh_out, time.strftime('%Y-%m-%d %H:%M:%S') + "\t" + ':'.join([str(i) for i in client_addr]) + "\t" + request

    def is_addr_allowed(self, client_addr):
        """Return true if the given client address (IP + port) is allowed to add keys."""
        return self.allow_ip.is_in_range(client_addr[0])


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
    ap.add_argument('-i', '--allow-ip', default=DEFAULT_ALLOW_IP)
    ap.add_argument('--codes', default=DEFAULT_CODES_PATH)
    args = ap.parse_args()
    run(settings=vars(args))
