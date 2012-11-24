#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import multiprocessing
import fcntl
import time
import os
import os.path
import sys
import re
import xml.dom.minidom
import socket

from datetime import datetime

from SDS.utils.mproc import global_lock
from SDS.utils.exception import SDSException

class SessionLoggerException(SDSException):
    pass

class SessionLogger:
    """ This is a multiprocessing safe logger. It should be used by the SDS to log information
    according the SDC 2010 XML format.
    
    Date and times should also include time zone.
    
    Times should be in seconds from the beginning of the dialogue.

    """

    lock = multiprocessing.RLock()

    def __init__(self):
        self.session_dir_name = multiprocessing.Array('c', ' ' * 1000)
        self.session_dir_name.value = ''

    def __repr__(self):
        return "SessionLogger()"

    @global_lock(lock)
    def get_date_str(self):
        """ Return current time in ISO format.

        It is useful when constricting file and directory names.
        """
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        dt += " " + time.tzname[time.localtime().tm_isdst]

        return dt

    @global_lock(lock)
    def get_time_str(self):
        """ Return current time in ISO format.

        It is useful when constricting file and directory names.
        """
        dt = datetime.now() - self.session_start_time

        return str(dt.total_seconds())
        
    @global_lock(lock)
    def session_start(self, output_dir):
        """ Records the target directory and create the template call log.
        """
        self.session_dir_name.value = output_dir

        f = open(os.path.join(self.session_dir_name.value, 'session.xml'), "w", 0)
        fcntl.lockf(f, fcntl.LOCK_EX)
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<dialogue>
</dialogue>
""")
        f.write('\n')
        fcntl.lockf(f, fcntl.LOCK_UN)
        f.close()
        
        self.session_start_time = datetime.now()

    @global_lock(lock)
    def session_end(self):
        """ Disable logging into the session specific directory
        """
        self.session_dir_name.value = ''

    @global_lock(lock)
    def get_session_dir_name(self):
        """ Return the directory where all the session related files should be stored.
        """
        return self.session_dir_name.value

    def cfg_formatter(self, message):
        """ Format the message - pretty print
        """

        s = '    ' + str(message)
        s = re.sub(r'\n', '\n    ', s)

        return s + '\n'

    def open_session_xml(self):
        """Opens the session xml file and locks it to prevent others to modify it."""

        self.f = open(os.path.join(self.session_dir_name.value, 'session.xml'), "r+", 0)
        fcntl.lockf(self.f, fcntl.LOCK_EX)

        doc = xml.dom.minidom.parse(self.f)

        return doc

    def close_session_xml(self, doc):
        """Saves the doc document into the session xml file, unlocks and closes the session xml file."""

        self.f.seek(0)
        self.f.truncate(0)

        x = doc.toprettyxml(encoding="UTF-8")
        for i in range(5):
            x = re.sub(r'\n\t*\n', '\n', x)
            x = re.sub(r'\n *\n', '\n', x)
        x = re.sub(r'\t', '    ', x)

        self.f.write(x)
        fcntl.lockf(self.f, fcntl.LOCK_UN)
        self.f.close()

    @global_lock(lock)
    def config(self, cfg):
        """ Adds the config tag to the session log.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("dialogue")

        if els:
            if els[0].firstChild:
                config = els[0].insertBefore(doc.createElement("config"), els[0].firstChild)
            else:
                config = els[0].appendChild(doc.createElement("config"))
            comment = config.appendChild(doc.createComment(self.cfg_formatter(cfg)))

        self.close_session_xml(doc)

    @global_lock(lock)
    def header(self, system_txt, version_txt):
        """ Adds host, date, system, and version info into the header element.
        The host and date will be derived automatically.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("dialogue")

        if els:
            header = els[0].appendChild(doc.createElement("header"))
            host = header.appendChild(doc.createElement("host"))
            host.appendChild(doc.createTextNode(socket.gethostname()))
            date = header.appendChild(doc.createElement("date"))
            date.appendChild(doc.createTextNode(self.get_date_str()))

            system = header.appendChild(doc.createElement("system"))
            system.appendChild(doc.createTextNode(system_txt))
            version = header.appendChild(doc.createElement("version"))
            version.appendChild(doc.createTextNode(version_txt))

        self.close_session_xml(doc)

    @global_lock(lock)
    def input_source(self, input_source):
        """Adds the input_source optional tag to the header."""
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("header")

        if els:
            i_s = els[0].appendChild(doc.createElement("input_source"))
            i_s.setAttribute("type", input_source)

        self.close_session_xml(doc)

    @global_lock(lock)
    def evaluation(self, num_turns, task_success, user_sat, score):
        """Adds the evaluation optional tag to the header."""
        pass

    def turn_count(self, doc, speaker):
        trns = doc.getElementsByTagName("turn")
        counter = 0
        
        if trns:
            for i in range(trns.length):
                if trns[i].getAttribute("speaker") == speaker:
                    counter += 1
            
            return counter
            
        return 0
        
#    @global_lock(lock)
    def turn(self, speaker):
        """ Adds a new turn at the end of the dialogue element.

        The turn_number for the speaker is automatically computed
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("dialogue")
        trns = self.turn_count(doc, speaker)
        
        if els:
            turn = els[0].appendChild(doc.createElement("turn"))
            turn.setAttribute("speaker", speaker)
            turn.setAttribute("turn_number", str(trns+1))
            turn.setAttribute("time", self.get_time_str())

        self.close_session_xml(doc)

#    @global_lock(lock)
    def dialogue_act(self, speaker, dialogue_act):
        """ Adds the dialogue_act element to the last "speaker" turn.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length-1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("dialogue_act"))
                da.setAttribute("time", self.get_time_str())
                da.appendChild(doc.createTextNode(str(dialogue_act)))
                break
        else:
            raise SessionLoggerException("Missing turn element for %s speaker" % speaker)

        self.close_session_xml(doc)

#    @global_lock(lock)
    def text(self, speaker, text):
        """ Adds the text (prompt) element to the last "speaker" turn.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length-1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("text"))
                da.setAttribute("time", self.get_time_str())
                da.appendChild(doc.createTextNode(str(text)))
                break
        else:
            raise SessionLoggerException("Missing turn element for %s speaker" % speaker)
            
        self.close_session_xml(doc)

    @global_lock(lock)
    def rec_start(self, speaker, fname):
        """ Adds the optional recorded input/output element to the last "speaker" turn.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length-1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("rec"))
                da.setAttribute("fname", fname)
                da.setAttribute("starttime", self.get_time_str())
                break
        else:
            raise SessionLoggerException("Missing turn element for %s speaker" % speaker)

        self.close_session_xml(doc)
        
    @global_lock(lock)
    def rec_end(self, fname):
        """ Stores the end time in the rec element with fname file.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("rec")

        for i in range(els.length-1, -1, -1):
            if els[i].getAttribute("fname") == fname:
                els[i].setAttribute("endtime", self.get_time_str())
                break
        else:
            raise SessionLoggerException("Missing rec element for %s fname" % fname)

        self.close_session_xml(doc)

    @global_lock(lock)
    def text_cost(self, speaker, cost):
        """ Adds the optional info about the TTS cost of the system prompt to the last system turn.
        """
        pass

    @global_lock(lock)
    def barge_in(self, speaker, tts_time, asr_time):
        """Add the optional barge_in element to the last system turn."""
        pass


    @global_lock(lock)
    def asr(self, speaker, nblist, confnet = None):
        """ Adds the asr nbest list to the last user turn.

        SDS Extension: It can also store the confusion network representation.
        """
        pass

    @global_lock(lock)
    def slu(self, speaker, nblist, confnet = None):
        """ Adds the slu nbest list to the last user turn.

        SDS Extension: It can also store the confusion network representation.
        """
        pass

    @global_lock(lock)
    def hangup(self, speaker):
        """ Adds the user hangup element to the last user turn.
        """

    ###########################################################################################
    ## The following functions define functionality above what was set in SDC 2010 XML
    ## logging format.
    ###########################################################################################

    @global_lock(lock)
    def dialogue_state(self, speaker, dstate):
        """ Adds the dialogue state to the log.

        This is an SDS extension.
        """
        pass

    @global_lock(lock)
    def belief_state(self, speaker, bstate):
        """ Adds the belief state to the log.

        This is an SDS extension.
        """
        pass
