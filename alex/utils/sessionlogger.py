#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

import multiprocessing
import time
import os
import os.path
import re
import xml.dom.minidom
import socket
import wave

from datetime import datetime

from alex.utils.mproc import mtime
from alex.utils.exdec import catch_ioerror
from alex.utils.exceptions import SessionLoggerException, SessionClosedException
from alex.utils.procname import set_proc_name


class SessionLogger(multiprocessing.Process):
    """
    This is a multiprocessing-safe logger. It should be used by the alex to log
    information according the SDC 2010 XML format.

    Date and times should also include time zone.

    Times should be in seconds from the beginning of the dialogue.

    """

    def __init__(self):
        multiprocessing.Process.__init__(self)

        self._session_dir_name = ''
        self._session_start_time = time.time()
        self._is_open = False   # whether the session is started

        # filename of the started recording
        self._rec_started = {}

        self.queue = multiprocessing.Queue()

    def set_close_event(self, close_event):
        self.close_event = close_event

    def set_cfg(self, cfg):
        self.cfg = cfg

    def __repr__(self):
        return "SessionLogger()"

    def __getattr__(self, key):
        """Queue all method calls for methods not known, Later the process will try to call these functions
        asynchronously.
        """
        @mtime('SessionLoggerQueue: '+key)
        def queue(*args, **kw):
            # print "Queueing a call", key, args, kw
            self.queue.put((key, args, kw))

        return queue

    def _get_date_str(self):
        """ Return current time in ISO format.

        It is useful when constructing file and directory names.
        """
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dt += " " + time.tzname[time.localtime().tm_isdst]

        return dt


    def _get_time_str(self):
        """ Return current time in ISO format.

        It is useful when constructing file and directory names.
        """
        dt = time.time() - self._session_start_time

        return "%.3f" % dt

    @mtime('seslog_session_start')
    def _session_start(self, output_dir):
        """ Records the target directory and creates the template call log.
        """

        self._session_dir_name = output_dir

        f = open(os.path.join(self._session_dir_name, 'session.xml'), "w", 0)
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<dialogue>
</dialogue>
""")
        f.write('\n')
        f.close()

        self._session_start_time = time.time()
        self._is_open = True

    def _flush(self):
        # close all opened rec_started files

        for f in self._rec_started:
            if self._rec_started[f]:
                self._rec_end(f)

    @mtime('seslog_session_end')
    def _session_end(self):
        """
        *WARNING: Deprecated* Disables logging into the session-specific directory.

        We better do not end a session because very often after the session_end() method is called there are still
        incoming messages. Therefore, it is better to wait for the session_start() method to set a
        new destination for the session log.

        """

        self._flush()
        self._session_dir_name = ''
        self._is_open = False

    def _cfg_formatter(self, message):
        """ Format the message - pretty print
        """

        s = '    ' + unicode(message)
        s = re.sub(r'\n', '\n    ', s)
        s = re.sub(r'--', '- -', s)  # XML does not allow -- in comment mode

        return s + '\n'

    def _open_session_xml(self):
        """Opens the session xml file and locks it to prevent others from
        modifying it.

        """

        self._f = open(os.path.join(self._session_dir_name, 'session.xml'), "r+", 0)
        # fcntl.lockf(self._f, fcntl.LOCK_EX)

        doc = xml.dom.minidom.parse(self._f)

        return doc

    def _close_session_xml(self, doc):
        """Saves the doc document into the session xml file, unlocks and closes
        the session xml file.

        """

        self._f.seek(0)
        self._f.truncate(0)

        x = doc.toprettyxml(encoding='utf-8')

        for i in range(5):
            x = re.sub(r'\n\t*\n', '\n', x)
            x = re.sub(r'\n *\n', '\n', x)
#            x = re.sub(r'>\n\t*(\w)', r'>\1', x)
        x = re.sub(r'\t', '    ', x)
#        x = unicode(x, encoding='utf-8')

        self._f.write(x)
        # fcntl.lockf(self._f, fcntl.LOCK_UN)
        self._f.close()

    @mtime('seslog_config')
    @catch_ioerror
    def _config(self, cfg):
        """ Adds the config tag to the session log.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("dialogue")

        if els:
            if els[0].firstChild:
                config = els[0].insertBefore(doc.createElement("config"), els[0].firstChild)
            else:
                config = els[0].appendChild(doc.createElement("config"))
            config.appendChild(doc.createComment(self._cfg_formatter(cfg)))

        self._close_session_xml(doc)

    @mtime('seslog_header')
    @catch_ioerror
    def _header(self, system_txt, version_txt):
        """ Adds host, date, system, and version info into the header element.
        The host and date will be derived automatically.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("dialogue")

        if els:
            header = els[0].appendChild(doc.createElement("header"))
            host = header.appendChild(doc.createElement("host"))
            host.appendChild(doc.createTextNode(socket.gethostname()))
            date = header.appendChild(doc.createElement("date"))
            date.appendChild(doc.createTextNode(self._get_date_str()))

            system = header.appendChild(doc.createElement("system"))
            system.appendChild(doc.createTextNode(system_txt))
            version = header.appendChild(doc.createElement("version"))
            version.appendChild(doc.createTextNode(version_txt))

        self._close_session_xml(doc)

    @mtime('seslog_input_source')
    @catch_ioerror
    def _input_source(self, input_source):
        """Adds the input_source optional tag to the header."""
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("header")

        if els:
            i_s = els[0].appendChild(doc.createElement("input_source"))
            i_s.setAttribute("type", input_source)

        self._close_session_xml(doc)

    @mtime('seslog_dialogue_rec_start')
    # @catch_ioerror - do not add! VIO catches the IOError
    def _dialogue_rec_start(self, speaker, fname):
        """ Adds the optional recorded input/output element to the last
        "speaker" turn.

        FIXME: It can happen that the session.xml is not created when this
        function is called.

        """
        doc = self._open_session_xml()

        els = doc.getElementsByTagName("dialogue")

        if els:
            da = els[0].appendChild(doc.createElement("dialogue_rec"))
            if speaker:
                da.setAttribute("speaker", speaker)
            da.setAttribute("fname", fname)
            da.setAttribute("starttime", self._get_time_str())
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException(("Missing dialogue element for %s speaker") % speaker)

        self._close_session_xml(doc)

    @mtime('seslog_dialogue_rec_end')
    # @catch_ioerror - do not add! VIO catches the IOError
    def _dialogue_rec_end(self, fname):
        """ Stores the end time in the dialogue_rec element with fname file.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("dialogue_rec")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("fname") == fname:
                els[i].setAttribute("endtime", self._get_time_str())
                break
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException("Missing dialogue_rec element for %s fname" % fname)

        self._close_session_xml(doc)

    @mtime('seslog_evaluation')
    @catch_ioerror
    def _evaluation(self, num_turns, task_success, user_sat, score):
        """Adds the evaluation optional tag to the header."""
        raise SessionLoggerException("Not implemented")

    def _turn_count(self, doc, speaker):
        trns = doc.getElementsByTagName("turn")
        counter = 0

        if trns:
            for i in range(trns.length):
                if trns[i].getAttribute("speaker") == speaker:
                    counter += 1

            return counter

        return 0

    @mtime('seslog_turn')
    @catch_ioerror
    def _turn(self, speaker):
        """ Adds a new turn at the end of the dialogue element.

        The turn_number for the speaker is automatically computed

        FIXME: It can happen that the session.xml is already closed when this
        function is called.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("dialogue")
        trns = self._turn_count(doc, speaker)

        if els:
            turn = els[0].appendChild(doc.createElement("turn"))
            turn.setAttribute("speaker", speaker)
            turn.setAttribute("turn_number", unicode(trns + 1))
            turn.setAttribute("time", self._get_time_str())

        self._close_session_xml(doc)

    @mtime('seslog_dialogue_act')
    @catch_ioerror
    def _dialogue_act(self, speaker, dialogue_act):
        """ Adds the dialogue_act element to the last "speaker" turn.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("dialogue_act"))
                da.setAttribute("time", self._get_time_str())
                da.appendChild(doc.createTextNode(unicode(dialogue_act)))
                break
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException(("Missing turn element for %s speaker") % speaker)

        self._close_session_xml(doc)

    @mtime('seslog_text')
    @catch_ioerror
    def _text(self, speaker, text, cost=None):
        """ Adds the text (prompt) element to the last "speaker" turn.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("text"))
                da.setAttribute("time", self._get_time_str())
                if cost:
                    da.setAttribute("cost", unicode(cost))
                da.appendChild(doc.createTextNode(unicode(text)))
                break
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException("Missing turn element for {spkr} speaker".format(spkr=speaker))

        self._close_session_xml(doc)

    @mtime('seslog_rec_start')
    @catch_ioerror
    def _rec_start(self, speaker, fname):
        """Adds the optional recorded input/output element to the last
        "speaker" turn.

        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("rec"))
                da.setAttribute("fname", fname)
                da.setAttribute("starttime", self._get_time_str())
                break
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException(("Missing turn element for the {spkr} speaker".format(spkr=speaker)))

        self._close_session_xml(doc)

        self._rec_started[fname] = wave.open(os.path.join(self._session_dir_name, fname), 'w')
        self._rec_started[fname].setnchannels(1)
        self._rec_started[fname].setsampwidth(2)
        self._rec_started[fname].setframerate(self.cfg['Audio']['sample_rate'])

    @mtime('seslog_rec_write')
    @catch_ioerror
    def _rec_write(self, fname, data_rec):
        """Write into open file recording.
        """
        self._rec_started[fname].writeframes(bytearray(data_rec))

    @mtime('seslog_rec_end')
    @catch_ioerror
    def _rec_end(self, fname):
        """ Stores the end time in the rec element with fname file.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("rec")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("fname") == fname:
                els[i].setAttribute("endtime", self._get_time_str())
                break
        else:
            self._close_session_xml(doc)
            self._rec_started[fname].close()
            self._rec_started[fname] = None
            raise SessionLoggerException(("Missing rec element for the {fname} fname.".format(fname=fname)))

        self._close_session_xml(doc)
        self._rec_started[fname].close()
        self._rec_started[fname] = None

    def _include_rec(self, turn, fname):
        if fname == "*":
            return True

        recs = turn.getElementsByTagName("rec")

        for rec in recs:
            if rec.getAttribute("fname") == fname:
                return True

        return False

    @mtime('seslog_asr')
    @catch_ioerror
    def _asr(self, speaker, fname, nblist, confnet=None):
        """ Adds the ASR nblist to the last speaker turn.

        alex Extension: It can also store the confusion network representation.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("turn")

        for el_idx in range(els.length - 1, -1, -1):
            if els[el_idx].getAttribute("speaker") == speaker and self._include_rec(els[el_idx], fname):
                asr = els[el_idx].appendChild(doc.createElement("asr"))

                for prob, hyp in nblist:
                    hyp_el = asr.appendChild(doc.createElement("hypothesis"))
                    hyp_el.setAttribute("p", "{0:.3f}".format(prob))
                    hyp_el.appendChild(doc.createTextNode(unicode(hyp)))

                if confnet:
                    cn = asr.appendChild(doc.createElement("confnet"))

                    for alts in confnet:
                        was = cn.appendChild(
                            doc.createElement("word_alternatives"))

                        for prob, word in alts:
                            wa = was.appendChild(doc.createElement("word"))
                            wa.setAttribute("p", "{0:.3f}".format(prob))
                            wa.appendChild(doc.createTextNode(unicode(word)))

                break
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException(("Missing turn element for %s speaker") % speaker)

        self._close_session_xml(doc)

    @mtime('seslog_slu')
    @catch_ioerror
    def _slu(self, speaker, fname, nblist, confnet=None):
        """ Adds the slu nbest list to the last speaker turn.

        alex Extension: It can also store the confusion network representation.
        The confnet must be an instance of DialogueActConfusionNetwork.

        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker and self._include_rec(els[i], fname):
                asr = els[i].appendChild(doc.createElement("slu"))

                for p, h in nblist:
                    hyp = asr.appendChild(doc.createElement("interpretation"))
                    hyp.setAttribute("p", "%.3f" % p)
                    hyp.appendChild(doc.createTextNode(unicode(h)))

                if confnet:
                    cn = asr.appendChild(doc.createElement("confnet"))

                    for p, dai in confnet:
                        sas = cn.appendChild(doc.createElement("dai_alternatives"))

                        daia = sas.appendChild(doc.createElement("dai"))
                        daia.setAttribute("p", "%.3f" % p)
                        daia.appendChild(doc.createTextNode(unicode(dai)))

                        daia = sas.appendChild(doc.createElement("dai"))
                        daia.setAttribute("p", "%.3f" % (1 - p))
                        daia.appendChild(doc.createTextNode("null()"))

                break
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException(("Missing turn element for %s speaker") % speaker)

        self._close_session_xml(doc)

    @mtime('seslog_barge_in')
    @catch_ioerror
    def _barge_in(self, speaker, tts_time=False, asr_time=False):
        """Add the optional barge-in element to the last speaker turn."""
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                da = els[i].appendChild(doc.createElement("barge-in"))
                da.setAttribute("time", self._get_time_str())
                if tts_time:
                    da.setAttribute("tts_time", self._get_time_str())
                if asr_time:
                    da.setAttribute("asr_time", self._get_time_str())
                break
        else:
            raise SessionLoggerException(("Missing turn element for %s speaker") % speaker)

        self._close_session_xml(doc)

    @mtime('seslog_hangup')
    @catch_ioerror
    def _hangup(self, speaker):
        """ Adds the user hangup element to the last user turn.
        """
        doc = self._open_session_xml()
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                els[i].appendChild(doc.createElement("hangup"))
                break
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException(("Missing turn element for %s speaker") % speaker)

        self._close_session_xml(doc)

    ########################################################################
    ## The following functions define functionality above what was set in ##
    ## SDC 2010 XML logging format.                                       ##
    ########################################################################

    def _last_turn_element(self, doc, speaker):
        """ Finds the XML element in the given open XML session
        which corresponds to the last turn for the given speaker.

        Closes the XML and throws an exception if the element cannot be found.
        """
        els = doc.getElementsByTagName("turn")

        for i in range(els.length - 1, -1, -1):
            if els[i].getAttribute("speaker") == speaker:
                return els[i]
        else:
            self._close_session_xml(doc)
            raise SessionLoggerException(("Missing turn element for %s speaker") % speaker)

    @mtime('seslog_dialogue_state')
    @catch_ioerror
    def _dialogue_state(self, speaker, dstate):
        """ Adds the dialogue state to the log.

        This is an alex extension.

        The dstate has the following structure:
         [state1, state2, ...]

        where state* has the following structure
        [ (slot_name1, slot_value1), (slot_name2, slot_value2), ...)

        """
        doc = self._open_session_xml()
        turn = self._last_turn_element(doc, speaker)

        for state in dstate:
            ds = turn.appendChild(doc.createElement("dialogue_state"))

            for slot_name, slot_value in state:
                sl = ds.appendChild(doc.createElement("slot"))
                sl.setAttribute("name", "%s" % slot_name)
                sl.appendChild(doc.createTextNode(unicode(slot_value)))

        self._close_session_xml(doc)

    @mtime('seslog_external_data_file')
    @catch_ioerror
    def _external_data_file(self, ftype, fname):
        """ Adds a link to an external data file (such as Google directions).
        This will create an <external> link with appropriate "type" and "fname"
        attributes.

        This is an alex extension.
        """
        doc = self._open_session_xml()
        turn = self._last_turn_element(doc, "system")
        el = turn.appendChild(doc.createElement("external"))
        el.setAttribute("type", ftype)
        el.setAttribute("fname", fname)
        self._close_session_xml(doc)

    def run(self):
        try:
            set_proc_name("Alex_SessionLogger")

            while 1:
                # Check the close event.
                if self.close_event.is_set():
                    return

                time.sleep(self.cfg['Hub']['main_loop_sleep_time'])

                if not self.queue.empty():
                    key, args, kw = self.queue.get()

                    attr = '_'+key
                    try:
                        # print 'Calling: ', key
                        cf = SessionLogger.__dict__[attr]
                        cf(self, *args, **kw)
                    except AttributeError:
                        print "SessionLogger: unknown method", key
                        raise
                    except SessionLoggerException as e:
                        print "Exception when logging:", key, args, kw
                        print e
                    except IOError:
                        if key == 'dialogue_rec_start':
                            # try once again later
                            self.queue.put((key, args, kw))
        except:
            print 'Uncaught exception in the SessionLogger process.'
            self.close_event.set()
            raise

