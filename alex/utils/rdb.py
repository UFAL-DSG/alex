#!/usr/bin/env python

import pdb
import socket
import sys

class Rdb(pdb.Pdb):
    def __init__(self, port=4446):
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.skt.bind((socket.gethostname(), port))
        self.skt.listen(1)
        print 'listening'
        (clientsocket, address) = self.skt.accept()
        handle = clientsocket.makefile('rw')
        pdb.Pdb.__init__(self, completekey='tab', stdin=handle, stdout=handle)
        sys.stdout = sys.stdin = handle

    def do_continue(self, arg):
        sys.stdout = self.old_stdout
        sys.stdin = self.old_stdin
        self.skt.close()
        self.set_continue()
        return 1

    do_c = do_cont = do_continue