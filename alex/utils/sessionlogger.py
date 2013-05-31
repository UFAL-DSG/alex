#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import fcntl
import time
import os
import os.path
import re
import xml.dom.minidom
import socket
import codecs

from datetime import datetime

from alex.utils.mproc import global_lock
from alex.utils.exception import AlexException
from alex.utils.exdec import catch_ioerror

import alex.utils.pdbonerror


class SessionLoggerException(AlexException):
    pass


class SessionClosedException(AlexException):
    pass

class SessionLogger:
    """ This is a multiprocessing safe logger. It should be used by the alex to
    log information according the SDC 2010 XML format.

    Date and times should also include time zone.

    Times should be in seconds from the beginning of the dialogue.

    """

    lock = multiprocessing.RLock()

    def __init__(self):
        self.session_dir_name = multiprocessing.Array('c', ' ' * 1000)
        self.session_dir_name.value = ''
        self.session_start_time = multiprocessing.Value('d', time.time())
        self._is_open = False   # whether the session is started

        # filename of the started recording
        self.rec_started_filename = None

    def __repr__(self):
        return "SessionLogger()"

    @global_lock(lock)
    def get_date_str(self):
        """ Return current time in ISO format.

        It is useful when constricting file and directory names.
        """
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dt += " " + time.tzname[time.localtime().tm_isdst]

        return dt

    @global_lock(lock)
    def get_time_str(self):
        """ Return current time in ISO format.

        It is useful when constricting file and directory names.
        """
        dt = time.time() - self.session_start_time.value

        return "%.3f" % dt

    @global_lock(lock)
    def session_start(self, output_dir):
        """ Records the target directory and creates the template call log.
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

        self.session_start_time.value = time.time()
        self._is_open = True

    def _flush(self):
        if self.rec_started_filename is not None:
            self.rec_end(self.rec_started_filename)
            self.rec_started_filename = None

    @global_lock(lock)
    def session_end(self):
        """ Disables logging into the session-specific directory.
        """
        self._flush()
        self.session_dir_name.value = ''
        self._is_open = False

    @global_lock(lock)
    def _get_is_open(self):
        return self._is_open

    is_open = property(_get_is_open)

    @global_lock(lock)
    def get_session_dir_name(self):
        """Returns the directory where all the session-related files should be
        stored.  If the session is not open, it raises
        a SessionClosedException.

        """
        if self._is_open:
            return self.session_dir_name.value
        else:
            raise SessionClosedException("There is no directory for a session "
                                         "that has been closed.")

    def cfg_formatter(self, message):
        """ Format the message - pretty print
        """

        s = '    ' + unicode(message)
        s = re.sub(r'\n', '\n    ', s)

        return s + '\n'

    def open_session_xml(self):
        """Opens the session xml file and locks it to prevent others from
        modifying it.

        """
        self.f = open(os.path.join(self.session_dir_name.value, 'session.xml'), "r+", 0)
        fcntl.lockf(self.f, fcntl.LOCK_EX)

        doc = xml.dom.minidom.parse(self.f)

        return doc

    def close_session_xml(self, doc):
        """Saves the doc document into the session xml file, unlocks and closes
        the session xml file.

        """

        self.f.seek(0)
        self.f.truncate(0)

        x = doc.toprettyxml(encoding='utf-8')

        for i in range(5):
            x = re.sub(r'\n\t*\n', '\n', x)
            x = re.sub(r'\n *\n', '\n', x)
#            x = re.sub(r'>\n\t*(\w)', r'>\1', x)
        x = re.sub(r'\t', '    ', x)
#        x = unicode(x, encoding='utf-8')

        self.f.write(x)
        fcntl.lockf(self.f, fcntl.LOCK_UN)
        self.f.close()

    @global_lock(lock)
    @catch_ioerror
    def config(self, cfg):
        """ Adds the config tag to the session log.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("dialogue")

        if els:
            if els[0].firstChild:
                config = els[0].insertBefore(
                    doc.createElement("config"), els[0].firstChild)
            else:
                config = els[0].appendChild(doc.createElement("config"))
            config.appendChild(doc.createComment(self.cfg_formatter(cfg)))

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
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
    @catch_ioerror
    def input_source(self, input_source):
        """Adds the input_source optional tag to the header."""
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("header")

        if els:
            i_s = els[0].appendChild(doc.createElement("input_source"))
            i_s.setAttribute("type", input_source)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def dialogue_rec_start(self, speaker, fname):
        """ Adds the optional recorded input/output element to the last
        "speaker" turn.

        FIXME: It can happen that the session.xml is not created when this
        function is called.

        """
        doc = self.open_session_xml()

        els = doc.getElementsByTagName("dialogue")

        if els:
            da = els[0].appendChild(doc.createElement("dialogue_rec"))
            if speaker:
                da.setAttribute("speaker", speaker)
            da.setAttribute("fname", fname)
            da.setAttribute("starttime", self.get_time_str())
        else:
            raise SessionLoggerException(("Missing dialogue element for %s "
                                          "speaker") % speaker)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def dialogue_rec_end(self, fname):
        """ Stores the end time in the dialogue_rec element with fname file.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("dialogue_rec")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("fname") == fname:
                els[i].setAttribute("endtime", self.get_time_str())
                break
        else:
            raise SessionLoggerException("Missing dialogue_rec element for "
                                         "%s fname" % fname)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def evaluation(self, num_turns, task_success, user_sat, score):
        """Adds the evaluation optional tag to the header."""
        raise SessionLoggerException("Not implemented")

    def turn_count(self, doc, speaker):
        trns = doc.getElementsByTagName("turn")
        counter = 0

        if trns:
            for i in range(trns.length):
                if trns[i].getAttribute("speaker") == speaker:
                    counter += 1

            return counter

        return 0

    @global_lock(lock)
    @catch_ioerror
    def turn(self, speaker):
        """ Adds a new turn at the end of the dialogue element.

        The turn_number for the speaker is automatically computed

        FIXME: It can happen that the session.xml is already closed when this
        function is called.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("dialogue")
        trns = self.turn_count(doc, speaker)

        if els:
            turn = els[0].appendChild(doc.createElement("turn"))
            turn.setAttribute("speaker", speaker)
            turn.setAttribute("turn_number", unicode(trns + 1))
            turn.setAttribute("time", self.get_time_str())

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def dialogue_act(self, speaker, dialogue_act):
        """ Adds the dialogue_act element to the last "speaker" turn.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("dialogue_act"))
                da.setAttribute("time", self.get_time_str())
                da.appendChild(doc.createTextNode(unicode(dialogue_act)))
                break
        else:
            raise SessionLoggerException(("Missing turn element for %s "
                                          "speaker") % speaker)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def text(self, speaker, text, cost=None):
        """ Adds the text (prompt) element to the last "speaker" turn.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("text"))
                da.setAttribute("time", self.get_time_str())
                if cost:
                    da.setAttribute("cost", unicode(cost))
                da.appendChild(doc.createTextNode(unicode(text)))
                break
        else:
            raise SessionLoggerException("Missing turn element for %s speaker" % speaker)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def rec_start(self, speaker, fname):
        """Adds the optional recorded input/output element to the last
        "speaker" turn.

        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("rec"))
                da.setAttribute("fname", fname)
                da.setAttribute("starttime", self.get_time_str())
                break
        else:
            raise SessionLoggerException(("Missing turn element for %s "
                                          "speaker") % speaker)

        self.rec_started_filename = fname
        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def rec_end(self, fname):
        """ Stores the end time in the rec element with fname file.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("rec")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("fname") == fname:
                els[i].setAttribute("endtime", self.get_time_str())
                break
        else:
            raise SessionLoggerException(("Missing rec element for %s "
                                          "fname") % fname)

        self.close_session_xml(doc)

        self.rec_started_filename = None

    @global_lock(lock)
    @catch_ioerror
    def asr(self, speaker, nblist, confnet=None):
        """ Adds the ASR nblist to the last speaker turn.

        alex Extension: It can also store the confusion network representation.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                asr = els[i].appendChild(doc.createElement("asr"))

                for p, h in nblist:
                    hyp = asr.appendChild(doc.createElement("hypothesis"))
                    hyp.setAttribute("p", "%.3f" % p)
                    hyp.appendChild(doc.createTextNode(unicode(h)))

                if confnet:
                    cn = asr.appendChild(doc.createElement("confnet"))

                    for alts in confnet:
                        was = cn.appendChild(
                            doc.createElement("word_alternatives"))

                        for p, w in alts:
                            wa = was.appendChild(doc.createElement("word"))
                            wa.setAttribute("p", "%.3f" % p)
                            wa.appendChild(doc.createTextNode(unicode(w)))

                break
        else:
            raise SessionLoggerException(("Missing turn element for %s "
                                          "speaker") % speaker)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def slu(self, speaker, nblist, confnet=None):
        """ Adds the slu nbest list to the last speaker turn.

        alex Extension: It can also store the confusion network representation.
        The confnet must be an instance of DialogueActConfusionNetwork.

        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                asr = els[i].appendChild(doc.createElement("slu"))

                for p, h in nblist:
                    hyp = asr.appendChild(doc.createElement("interpretation"))
                    hyp.setAttribute("p", "%.3f" % p)
                    hyp.appendChild(doc.createTextNode(unicode(h)))

                if confnet:
                    cn = asr.appendChild(doc.createElement("confnet"))

                    for p, dai in confnet:
                        sas = cn.appendChild(
                            doc.createElement("dai_alternatives"))

                        daia = sas.appendChild(doc.createElement("dai"))
                        daia.setAttribute("p", "%.3f" % p)
                        daia.appendChild(doc.createTextNode(unicode(dai)))

                        daia = sas.appendChild(doc.createElement("dai"))
                        daia.setAttribute("p", "%.3f" % (1 - p))
                        daia.appendChild(doc.createTextNode("null()"))

                break
        else:
            raise SessionLoggerException(("Missing turn element for %s "
                                          "speaker") % speaker)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def barge_in(self, speaker, tts_time=False, asr_time=False):
        """Add the optional barge-in element to the last speaker turn."""
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("barge-in"))
                if tts_time:
                    da.setAttribute("tts_time", self.get_time_str())
                if asr_time:
                    da.setAttribute("asr_time", self.get_time_str())
                break
        else:
            raise SessionLoggerException(("Missing turn element for %s "
                                          "speaker") % speaker)

        self.close_session_xml(doc)

    @global_lock(lock)
    @catch_ioerror
    def hangup(self, speaker):
        """ Adds the user hangup element to the last user turn.
        """
        doc = self.open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                els[i].appendChild(doc.createElement("hangup"))
                break
        else:
            raise SessionLoggerException(("Missing turn element for %s "
                                          "speaker") % speaker)

        self.close_session_xml(doc)

    ########################################################################
    ## The following functions define functionality above what was set in ##
    ## SDC 2010 XML logging format.                                       ##
    ########################################################################

    @global_lock(lock)
    @catch_ioerror
    def dialogue_state(self, speaker, dstate):
        """ Adds the dialogue state to the log.

        This is an alex extension.
        """
        raise SessionLoggerException("Not implemented")

    @global_lock(lock)
    @catch_ioerror
    def belief_state(self, speaker, bstate):
        """ Adds the belief state to the log.

        This is an alex extension.
        """
        raise SessionLoggerException("Not implemented")
