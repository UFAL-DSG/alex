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

from datetime import datetime

from SDS.utils.mproc import global_lock

class SessionLogger:
    """ This is a multiprocessing safe logger. It should be used by the SDS to log information
    according the SDC 2010 XML format.

    """

    lock = multiprocessing.RLock()

    def __init__(self):
        self.session_dir_name = multiprocessing.Array('c', ' ' * 1000)
        self.session_dir_name.value = ''

    @global_lock(lock)
    def get_time_str(self):
        """ Return current time in ISO format.

        It is useful when constricting file and directory names.
        """
        return datetime.now().isoformat('-').replace(':', '-')

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


    @global_lock(lock)
    def header(self, system, version):
        """
        The host and date will be derived automatically.
        """
        pass

    @global_lock(lock)
    def input_source(self, input_source):
        """Adds the input_source optional tag to the header."""
        pass

    @global_lock(lock)
    def evaluation(self, num_turns, task_success, user_sat, score):
        """Adds the evaluation optional tag to the header."""
        pass

    @global_lock(lock)
    def turn(self, speaker):
        """

        The turn_number for the speaker is automatically computed
        """

    @global_lock(lock)
    def system_dialogue_act(self, dialogue_act):
        """ Adds the dialogue_act tag to the last system turn.
        """
        pass

    @global_lock(lock)
    def system_text(self, dialogue_act):
        """ Adds the text (prompt) tag to the last system turn.
        """
        pass

    @global_lock(lock)
    def system_rec(self, fname, starttime, endtime):
        """ Adds the optional recorded system prompt tag to the last system turn.
        """
        pass

    @global_lock(lock)
    def system_text_cost(self, cost):
        """ Adds the optional info about the TTS cost of the system prompt to the last system turn.
        """
        pass

    @global_lock(lock)
    def barge_in(self, tts_time, asr_time):
        """Add the optional barge_in tag to the last system turn."""
        pass


    @global_lock(lock)
    def user_rec(self, fname, starttime, endtime):
        """ Adds the recorded user input tag to the last user turn.
        """
        pass

    @global_lock(lock)
    def user_asr(self, nblist, confnet = None):
        """ Adds the asr nbest list to the last user turn.

        SDS Extension: It can also store the confusion network representation.
        """
        pass

    @global_lock(lock)
    def user_slu(self, nblist, confnet = None):
        """ Adds the slu nbest list to the last user turn.

        SDS Extension: It can also store the confusion network representation.
        """
        pass

    @global_lock(lock)
    def user_hangup(self):
        """ Adds the user hangup tag to the last user turn.
        """

    ###########################################################################################
    ## The following functions define functionality above what was set in SDC 2010 XML
    ## logging format.
    ###########################################################################################

    @global_lock(lock)
    def dialogue_state(self, dstate):
        """ Adds the dialogue state to the log.

        This is an SDS extension.
        """
        pass

    @global_lock(lock)
    def belief_state(self, bstate):
        """ Adds the belief state to the log.

        This is an SDS extension.
        """
        pass
