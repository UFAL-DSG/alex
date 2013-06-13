#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# TODO: Propagate timeout setting.

from __future__ import unicode_literals

if __name__ == "__main__":
    import autopath

import os
import os.path
import socket
import struct
import subprocess
import time
import xml.dom.minidom

from alex.components.asr.exception import ASRException
from alex.components.asr.utterance import UtteranceNBList, Utterance, \
    UtteranceConfusionNetwork
from alex.utils.various import get_text_from_xml_node


class JuliusASRException(ASRException):
    pass


class JuliusASRTimeoutException(ASRException):
    pass


class JuliusASR(object):
    """\
    Uses Julius ASR service to recognize recorded audio.

    The main function, `get_results`, returns the hypotheses as an n-best list
    and a confusion network.  The function for asynchronous output, `hyp_out`,
    returns just the confusion network.

    """

    def __init__(self, cfg, popen_kwargs=dict()):
        self.recognition_on = False

        self.cfg = cfg
        self.debug = cfg['ASR']['Julius'].get('debug', False)
        self.julius_server = None
        self.hostname = self.cfg['ASR']['Julius']['hostname']
        self.serverport = self.cfg['ASR']['Julius']['serverport']
        self.adinnetport = self.cfg['ASR']['Julius']['adinnetport']
        self.reuse_server = self.cfg['ASR']['Julius']['reuse_server']
        self.pidfile = self.cfg['ASR']['Julius']['pidfile']
        self.jconf_fname = self.cfg['ASR']['Julius']['jconffile']
        self.log_fname = self.cfg['ASR']['Julius']['logfile']
        self.logfile = None
        self.jbin = self.cfg['ASR']['Julius']['binary']
        self.msg_timeout = self.cfg['ASR']['Julius'].get('msg_timeout', 0.3)
        self.timeout = self.cfg['ASR']['Julius'].get('timeout', 2.0)

        system_logger = self.cfg['Logging']['system_logger']
        try:
            if self.reuse_server:
                # reinit hack for julius
                os.system("killall -USR1 julius")
            if self.reuse_server and self.is_server_running():
                # If we should reuse server and it is running, it's perfect
                # and we will do nothing.
                system_logger.debug("Brilliant, Julius is already running.")
                self.open_adinnet()
                return
            elif not self.reuse_server and self.is_server_running():
                if os.path.isfile(self.pidfile):
                    self.kill_my_julius()
                    system_logger.debug("I just commited murder, Julius is "
                                        "dead!")
                else:
                    self.kill_all_juliuses()
                    system_logger.debug("I just killed ALL JULIŌS!")

            system_logger.debug("Starting the Julius ASR server...")
            self.start_server(popen_kwargs)
            if not self.wait():
                raise JuliusASRTimeoutException(
                    'Could not wait for Julius to start up.')

            system_logger.debug("Connected to Julius.")
            if not self.wait(test=self.is_adinnet_open):
                raise JuliusASRTimeoutException(
                    'Could not wait for adinnet to open.')
        except Exception as e:
            system_logger.debug("There was a problem with starting the "
                                "Julius ASR server: {msg!s}".format(msg=e))
            # DEBUG
            import sys
            sys.excepthook(*sys.exc_info())
            # Always kill the Julius ASR server when there is a problem.
            if self.julius_server:
                system_logger.debug("Killing the Julius ASR server!")
                self.julius_server.kill()

            system_logger.debug("Exiting!")
            exit(0)

    def __del__(self):
        # FIXME We might want to rewrite this functionality as a context
        # manager. Cf.
        # http://stackoverflow.com/questions/865115/how-do-i-correctly-clean-up-a-python-object.
        if not self.reuse_server:
            self.julius_server.terminate()
            time.sleep(1)
            self.julius_server.kill()
        if self.logfile:
            self.logfile.close()

    def is_server_running(self):
        # Try to connect to the server.
        try:
            self.connect_to_server()
        except socket.error:
            return False
        return True

    def is_adinnet_open(self):
        try:
            self.open_adinnet()
        except socket.error:
            return False
        return True

    def wait(self, test=None):
        """Waits until the server starts up.

        Returns whether the server is started at the time of returning. As
        a side effect, the test method typically changes the state of the thing
        it is testing (e.g., connects self to the Julius server).

        Arguments:
            - test: a method to use as a test whether the event waited for has
                    already happened
        """
        if test is None:
            test = self.is_server_running
        time_waited = 0.
        wait_incr = self.cfg['ASR']['Julius']['start_wait_time']
        max_wait_time = self.cfg['ASR']['Julius']['start_max_wait_time']
        while time_waited <= max_wait_time:
            is_running = test()
            if is_running:
                break
            time.sleep(wait_incr)
            time_waited += wait_incr
        return is_running

    def kill_my_julius(self):
        with open(self.pidfile) as pidfile:
            pid = pidfile.read()

        os.system('kill -9 {pid}'.format(pid=pid))

    @staticmethod
    def kill_all_juliuses():
        os.system('killall julius')

    def save_pid(self, pid):
        with open(self.pidfile, "w") as f_out:
            f_out.write(str(pid))

    def start_server(self, popen_kwargs=dict()):
        jconf_fname = self.jconf_fname
        self.logfile = open(self.log_fname, 'a+')
        jbin = self.jbin

        # Copy configuration from the Python cfg file to Julius jconf file.
        with open(jconf_fname, 'w') as jconf_file:
            jconf_dict = self.cfg['ASR']['Julius']['jconf']
            jconf_file.writelines(
                '{key} {val}\n'.format(key=key, val=val)
                for (key, val) in sorted(jconf_dict.iteritems()))

        # Kill all running instances of the Julius ASR server.
        if self.cfg['ASR']['Julius']['killall']:
            self.kill_all_juliuses()

        # Combine the default Popen arguments with those supplied by the
        # caller.
        usr_popen_kwargs = popen_kwargs
        popen_kwargs = {'stdout': self.logfile,
                        'bufsize': 0}
        popen_kwargs.update(usr_popen_kwargs)

        # Start the server with the -debug option.
        # With this option, it does not generate segfaults.
        self.julius_server = subprocess.Popen(
                [jbin, '-debug', '-C', jconf_fname], **popen_kwargs)
        # XXX If using shell in Popen, beware that Julius gets another
        # pid than the return value of Popen.
        self.save_pid(self.julius_server.pid)

    def connect_to_server(self):
        """Connects to the Julius ASR server to start recognition and receive
        the recognition output."""

        self.s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s_socket.connect((self.hostname, self.serverport))
        self.s_socket.setblocking(0)

    def open_adinnet(self):
        """Open the audio connection for sending the incoming frames."""

        self.a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.a_socket.connect((self.hostname, self.adinnetport))
        print 'adinnet opened'

    def send_frame(self, frame):
        """Sends one frame of audio data to the Julius ASR"""

        self.a_socket.sendall(struct.pack("i", len(frame)))
        self.a_socket.sendall(frame)

    def audio_finished(self):
        """"Informs the Julius ASR about the end of segment and that the
        hypothesis should be finalized."""

        self.a_socket.sendall(struct.pack("i", 0))
        self.recognition_on = False

    def read_audio_command(self):
        """Reads audio command from the Julius adinnet interface.

        Command:
          '0' - pause
          '1' - resume
          '2' - terminate
        """
        self.a_socket.setblocking(0)
        cmd = self.a_socket.recv(1)
        self.a_socket.setblocking(1)
        return cmd

    def read_server_message(self, timeout=0.3):
        """\
        Reads a complete message from the Julius ASR server.

        A complete message is denoted by a period on a new line at the end of
        the string.

        Timeout specifies how long it will wait for the end of message.
        """
        results = ""
        time_slept = 0.0

        # FIXME: Count real time elapsed.
        while time_slept < timeout:
            try:
                if self.debug >= 2:
                    print "receiving"
                results += self.s_socket.recv(1)
            except socket.error as ex:
                # errno = ex.errno
                # FIXME: We would like to determine (by the errno) what
                # happened.  If the server dies, there will be a deadlock.
                # However, in the situations seen so far, errno on its own does
                # not provide the necessary information.
                if not results:
                    if self.debug:
                        print "ERROR: ", ex
                        print "results: ", results
                    # There are no data waiting for us.
                    return None

            if results.endswith("\n.\n"):
                if self.debug:
                    print "***** results retrieved:", results
                results = results[:-3].strip()
                break
            else:
                # We already read some data but we did not receive the
                # final period, so continue reading.
                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])
                time_slept += self.cfg['Hub']['main_loop_sleep_time']
                if self.debug >= 2:
                    print "rm.time_slept:", time_slept
        else:
            if self.debug:
                print "**** results so far: ", results
            raise JuliusASRTimeoutException(
                "Timeout when waiting for the Julius server message.")

        if self.debug:
            print "rm.return:", results
        return results

    def get_results(self, timeout=0.6):
        """"\
        Waits for the complete recognition results from the Julius ASR server.

        Timeout specifies how long it will wait for the end of message.
        """
        msg = ""

        # Get results from the server.
        time_slept = 0.0
        while time_slept < timeout:
            msg_part = self.read_server_message(self.msg_timeout)
            if not msg_part:
                # Wait and check whether there is a message.
                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])
                time_slept += self.cfg['Hub']['main_loop_sleep_time']
                if self.debug >= 2:
                    print "gr.time_slept:", time_slept
                continue

            msg += msg_part + '\n'

            if self.debug:
                print msg

            if '<CONFNET>' in msg:
                break
        else:
            raise JuliusASRTimeoutException(
                "Timeout when waiting for the Julius server results.")

        # Process the results.
        """ Typical result returned by the Julius ASR.

          <STARTPROC/>
          <INPUT STATUS="LISTEN" TIME="1343896296"/>
          <INPUT STATUS="STARTREC" TIME="1343896311"/>
          <STARTRECOG/>
          <INPUT STATUS="ENDREC" TIME="1343896312"/>
          <ENDRECOG/>
          <INPUTPARAM FRAMES="164" MSEC="1640"/>
          <RECOGOUT>
            <SHYPO RANK="1" SCORE="-7250.111328">
              <WHYPO WORD="" CLASSID="<s>" PHONE="sil" CM="0.887"/>
              <WHYPO WORD="I'M" CLASSID="I'M" PHONE="ah m" CM="0.705"/>
              <WHYPO WORD="LOOKING" CLASSID="LOOKING" PHONE="l uh k ih ng" CM="0.992"/>
              <WHYPO WORD="FOR" CLASSID="FOR" PHONE="f er" CM="0.757"/>
              <WHYPO WORD="A" CLASSID="A" PHONE="ah" CM="0.672"/>
              <WHYPO WORD="PUB" CLASSID="PUB" PHONE="p ah b" CM="0.409"/>
              <WHYPO WORD="" CLASSID="</s>" PHONE="sil" CM="1.000"/>
            </SHYPO>
          </RECOGOUT>
          <GRAPHOUT NODENUM="43" ARCNUM="70">
              <NODE GID="0" WORD="" CLASSID="<s>" PHONE="sil" BEGIN="0" END="2"/>
              <NODE GID="1" WORD="" CLASSID="<s>" PHONE="sil" BEGIN="0" END="3"/>
              <NODE GID="2" WORD="" CLASSID="<s>" PHONE="sil" BEGIN="0" END="4"/>
              <NODE GID="3" WORD="I" CLASSID="I" PHONE="ay" BEGIN="3" END="5"/>
              <NODE GID="4" WORD="NO" CLASSID="NO" PHONE="n ow" BEGIN="3" END="7"/>
              <NODE GID="5" WORD="I" CLASSID="I" PHONE="ay" BEGIN="4" END="6"/>
              <NODE GID="6" WORD="UH" CLASSID="UH" PHONE="ah" BEGIN="4" END="6"/>
              <NODE GID="7" WORD="I'M" CLASSID="I'M" PHONE="ay m" BEGIN="4" END="27"/>

              ...

              <NODE GID="38" WORD="PUB" CLASSID="PUB" PHONE="p ah b" BEGIN="79" END="104"/>
              <NODE GID="39" WORD="AH" CLASSID="AH" PHONE="aa" BEGIN="81" END="110"/>
              <NODE GID="40" WORD="LOT" CLASSID="LOT" PHONE="l aa t" BEGIN="81" END="110"/>
              <NODE GID="41" WORD="" CLASSID="</s>" PHONE="sil" BEGIN="105" END="163"/>
              <NODE GID="42" WORD="" CLASSID="</s>" PHONE="sil" BEGIN="111" END="163"/>
              <ARC FROM="0" TO="4"/>
              <ARC FROM="0" TO="3"/>
              <ARC FROM="1" TO="7"/>
              <ARC FROM="1" TO="5"/>
              <ARC FROM="1" TO="6"/>

              ...

              <ARC FROM="38" TO="41"/>
              <ARC FROM="39" TO="42"/>
              <ARC FROM="40" TO="42"/>
          </GRAPHOUT>
          <CONFNET>
            <WORD>
              <ALTERNATIVE PROB="1.000"></ALTERNATIVE>
            </WORD>
            <WORD>
              <ALTERNATIVE PROB="0.950">I</ALTERNATIVE>
              <ALTERNATIVE PROB="0.020">HI</ALTERNATIVE>
              <ALTERNATIVE PROB="0.013">NO</ALTERNATIVE>
              <ALTERNATIVE PROB="0.010"></ALTERNATIVE>
              <ALTERNATIVE PROB="0.006">UH</ALTERNATIVE>
            </WORD>
            <WORD>
              <ALTERNATIVE PROB="0.945">AM</ALTERNATIVE>
              <ALTERNATIVE PROB="0.055">I'M</ALTERNATIVE>
            </WORD>
            <WORD>
              <ALTERNATIVE PROB="1.000">LOOKING</ALTERNATIVE>
            </WORD>
            <WORD>
              <ALTERNATIVE PROB="1.000">FOR</ALTERNATIVE>
            </WORD>
            <WORD>
              <ALTERNATIVE PROB="1.000">A</ALTERNATIVE>
            </WORD>
            <WORD>
              <ALTERNATIVE PROB="0.963">PUB</ALTERNATIVE>
              <ALTERNATIVE PROB="0.016">AH</ALTERNATIVE>
              <ALTERNATIVE PROB="0.012">BAR</ALTERNATIVE>
              <ALTERNATIVE PROB="0.008">LOT</ALTERNATIVE>
            </WORD>
            <WORD>
              <ALTERNATIVE PROB="1.000"></ALTERNATIVE>
            </WORD>
          </CONFNET>
          <INPUT STATUS="LISTEN" TIME="1343896312"/>

        """
        msg = "<RESULTS>" + msg + "</RESULTS>"
        msg = msg.replace("<s>", "&lt;s&gt;").replace("</s>", "&lt;/s&gt;")

        nblist = UtteranceNBList()

        doc = xml.dom.minidom.parseString(msg)
        recogout = doc.getElementsByTagName("RECOGOUT")
        for el in recogout:
            shypo = el.getElementsByTagName("SHYPO")
            for el in shypo:
                whypo = el.getElementsByTagName("WHYPO")
                utterance = ""
                cm = 1.0
                for el in whypo:
                    word = el.getAttribute("WORD")
                    utterance += " " + word
                    if word:
                        cm *= float(el.getAttribute("CM"))
                nblist.add(cm, Utterance(utterance))

        nblist.merge()
        nblist.add_other()

        cn = UtteranceConfusionNetwork()

        confnet = doc.getElementsByTagName("CONFNET")
        for el in confnet:
            word = el.getElementsByTagName("WORD")
            for el in word:
                alternative = el.getElementsByTagName("ALTERNATIVE")
                word_list = []
                for el in alternative:
                    prob = float(el.getAttribute("PROB"))
                    text = get_text_from_xml_node(el)
                    word_list.append([prob, text])

                # Filter out empty hypotheses.
                if len(word_list) == 0:
                    continue
                if len(word_list) == 1 and len(word_list[0][1]) == 0:
                    continue

                # Add the word into the confusion network.
                cn.add(word_list)

        cn.merge()
        cn.normalise()
        cn.prune()
        cn.normalise()
        cn.sort()

        return nblist, cn

    def flush(self):
        """\
        Sends a command to the Julius ASR to terminate recognition and get
        ready for new recognition.

        """
        if self.recognition_on:
            self.audio_finished()

            nblist, cn = self.get_results()
            # Read any leftovers.
            while True:
                if self.read_server_message() is None:
                    break

        return

    def rec_in(self, frame):
        """\
        This defines asynchronous interface for speech recognition.

        Call this input function with audio data belonging into one speech
        segment that should be recognized.

        Output hypothesis is obtained by calling hyp_out().
        """

        self.recognition_on = True
        self.send_frame(frame.payload)

        return

    def hyp_out(self):
        """\
        This defines asynchronous interface for speech recognition.

        Returns recognizers hypotheses about the input speech audio and
        a confusion network for the input.
        """

        # Read all messages accidentally left in the socket from the Julius ASR
        # server before.
        # A new ASR hypothesis is decoded.
        while True:
            msg = self.read_server_message()
            if msg is None:
                break

        if self.recognition_on:
            self.audio_finished()

            nblist, cn = self.get_results(timeout=self.timeout)

            return cn

        raise JuliusASRException("No ASR hypothesis is available since the "
                                 "recognition has not started.")
