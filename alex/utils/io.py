#!/usr/bin/env python
# vim: set fileencoding=utf-8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

from multiprocessing import Process
from time import sleep

DEBUG = False
# DEBUG = True


class GrepFilter(Process):
    def __init__(self, stdin, stdout, breakchar='\n'):
        Process.__init__(self)
        self.stdin = stdin
        self.stdout = stdout
        self.buf = ''
        self.breakchar = breakchar
        self.listeners = list()  # :: [(regex, callback)]
        self.valid = list()      # :: [?is_listener_valid]
        self.closed = False

    def add_listener(self, regex, callback):
        """\
        Adds a listener to the output strings.

        Arguments:
            regex -- the compiled regular expression to look for
                (`regex.search') in any piece of output
            callback -- a callable that is invoked for output where `regex' was
                found.  This will be called like this:

                    outputting &= callback(output_unicode_str)

                That means, callback should take the unicode string argument
                containing what would have been output and return a boolean
                value which is True iff outputting should stop.

        Returns the index of the listener for later reference.

        """
        if all(self.valid):
            idx = len(self.listeners)
            self.listeners.append((regex, callback))
            self.valid.append(True)
        else:
            idx = self.valid.index(False)
            self.listeners[idx] = (regex, callback)
            self.valid[idx] = True
        return idx

    def remove_listener(self, listener_idx):
        if listener_idx >= len(self.listeners):
            raise IndexError('Listener index out of bounds.')
        if listener_idx == len(self.listeners) - 1:
            del self.listeners[-1]
            del self.valid[-1]
        else:
            self.valid[listener_idx] = False

    def flush(self, force=True):
        flushing = False
        # while self.stdin.poll():
            # indata = self.stdin.recv()
        while True:
            indata = self.stdin.read()
            if not indata:
                break

            flushing |= self.breakchar in indata
            self.buf += indata
            if DEBUG:
                print "grep: stdin received:", indata
                print "flushing:", flushing
                print "self.buf:", self.buf
            if force and self.buf and self.buf[-1] != self.breakchar:
                self.buf += self.breakchar
                flushing = True
        if flushing:
            chunks = self.buf.split(self.breakchar)
            if DEBUG:
                print "chunks:", chunks
            self.buf = chunks[-1]
            del chunks[-1]
            map(self.write, chunks)

    def write(self, unistr):
        # DEBUG
        if DEBUG:
            print
            print 'Outputting "{}"'.format(unistr)

        outputting = True
        for regex, callback in self.listeners:
            if regex.search(unistr):
                outputting &= callback(unistr)
        # DEBUG
        if DEBUG:
            print 'outputting={}'.format(outputting)
            print

        if outputting:
            if self.closed:
                raise Exception('The output stream has already been closed!')
            self.stdout.write(unistr + self.breakchar)
        else:
            self.closed = True

    def run(self):
        while True:
            self.flush(False)
            sleep(.1)


# XXX This is very provisional.
def test_grep_filter():
    # from StringIO import StringIO
    from subprocess import Popen, PIPE
    import re
    import sys

    devnull = open('/dev/null', 'a+')
    producer = Popen(
        ['head', '-n', '3', __file__], stdout=PIPE, stderr=devnull)

    # sio = StringIO()
    sio = sys.stdout
    gio = GrepFilter(producer.stdout, sio)

    def gfunc(outstr):
        print "(II) match found:", outstr
        # return False
        return True
    rx = re.compile('ho', re.I)
    gio.add_listener(rx, gfunc)
    gio.start()

    if DEBUG:
        print producer.stdout
        sleep(1.)
        from pprint import pprint
        pprint(producer.__dict__.items())

    gio.flush()
    gio.terminate()


# XXX This is very provisional.
if __name__ == "__main__":
    test_grep_filter()
