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

The API
-------
- it accepts three query parameters: a,q and r
- it returns simple JSON with one node "response" [yes,no,success,online]
- if a is "1" (?q=CODE&a=1), then CODE is added and the response is "success"
- if r is "1" (?q=CODE&r=1), then CODE is removed and the response is "success"
- if CODE is present in "code_path" file it returns "yes" otherwise "no"
- if CODE is equal to "test" it sends "online" in response - connection check
- if CODE is equal to "task", a random HTML representation of a task is returned

Usage
-----

./server_ssl2.py [--port XXXX] [--key path/to/file.key] [--cert path/to/file.crt]
'''
import codecs
import json
from BaseHTTPServer import BaseHTTPRequestHandler
from urlparse import urlparse
import os
import SocketServer
import argparse
import random

code_path = "./codes"
log_path = "./log"
task_path = "./tasks"


class Handler(BaseHTTPRequestHandler):

    def read_codes(self, path):
        data = set()
        if not os.path.isfile(path):
            return data
        with codecs.open(path, 'r', 'UTF-8') as fh_in:
            for line in fh_in:
                line = line.strip()
                if len(line) > 0:
                    data.add(line)
        return data

    def remove_code(self, path, code):
        data = self.read_codes(path)
        with codecs.open(path, "w", 'UTF-8') as fh_out:
            for line in data:
                if line != code:
                    print >> fh_out, line

    def add_code(self, path, code):
        data = self.read_codes(path)
        data.add(code)
        with codecs.open(path, "w", 'UTF-8') as fh_out:
            for line in data:
                print >> fh_out, line

    def log_GET(self, path, get):
        with codecs.open(path, "a", 'UTF-8') as fh_out:
            print >> fh_out, get

    def do_GET(self):
        """Main method that handles a GET request from the client."""
        response = ""
        try:
            self.log_GET(log_path, str(self.path))

            codes = self.read_codes(code_path)

            query = urlparse(self.path).query

            query_components = dict(qc.split("=") for qc in query.split("&"))
            query_code = query_components["q"]

            add = query_components["a"] if "a" in query_components else "0"
            remove = query_components["r"] if "r" in query_components else "0"
            # callback = query_components["callback"] if query_components.has_key("callback") else ""

            if query_code == "test":
                response = "online"
            elif query_code == "task":
                response = self.get_random_task()
            elif add == "1":
                self.add_code(code_path, query_code)
                response = "success"
            elif remove == "1":
                self.remove_code(code_path, query_code)
                response = "success"
            else:
                response = 'yes' if query_code in codes else 'no'
        except Exception:
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
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True,
                 cert_file=None, key_file=None):
        """Constructor. May be extended, do not override."""

        # read the tasks and store them for reuse
        self.tasks = self.read_tasks(task_path)
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, False)

        # initialize SSL connection
        mydir = os.path.dirname(__file__)
        if key_file is None:
            key_file = os.path.join(mydir, 'server.key')
        if cert_file is None:
            cert_file = os.path.join(mydir, 'server.crt')

        import ssl
        self.socket = ssl.wrap_socket(self.socket,
                                      keyfile=key_file,
                                      certfile=cert_file,
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
        das, sents = random.choice(self.server.tasks)
        text = '<ol>\n'
        for sent in sents.split('\t'):
            text += '<li>' + sent + '</li>\n'
        text += '</ol>\n'
        return text


def run(server_class=SSLTCPServer, port=443, cert_file=None, key_file=None):
    httpd = server_class(('', port), Handler, True, cert_file, key_file)
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
    ap.add_argument('-p', '--port', type=int, default=443)
    ap.add_argument('-c', '--cert')
    ap.add_argument('-k', '--key')
    args = ap.parse_args()
    run(port=args.port, cert_file=args.cert, key_file=args.key)
