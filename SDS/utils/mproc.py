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

""" Implements useful classes for handling multiprocessing implementation of the SDS.
"""

def local_lock():
    """This decorator makes the decorated function thread safe.

    For each function it creates unique lock.
    """
    lock = multiprocessing.Lock()

    def decorator(user_function):
        @functools.wraps(user_function)
        def wraper(*args, **kw):
            lock.acquire()
            try:
                return user_function(*args, **kw)
            except Exception as e:
                raise e
            finally:
                lock.release()

        return wraper

    return decorator


def global_lock(lock):
    """This decorator makes the decorated function thread safe.

    It uses provided global lock.
    """
    def decorator(user_function):
        @functools.wraps(user_function)
        def wraper(*args, **kw):
            lock.acquire()
            try:
                return user_function(*args, **kw)
            except Exception as e:
                raise e
            finally:
                lock.release()

        return wraper

    return decorator


def file_lock(file_name):
    """ Multiprocessing lock using files. Lock on a specific file.
    """
    lock_file = open(file_name, 'w')
    fcntl.lockf(lock_file, fcntl.LOCK_EX)
    return lock_file

def file_unlock(lock_file):
    """ Multiprocessing lock using files. Unlock on a specific file.
    """
    fcntl.lockf(lock_file, fcntl.LOCK_UN)
    lock_file.close()

class InstanceID:
    """ This class provides unique ids to all instances of objects inheriting from this class.
    """

    lock = multiprocessing.Lock()
    instance_id = 0

    @global_lock(lock)
    def get_instance_id(self):
        InstanceID.instance_id += 1
        return InstanceID.instance_id

class SystemLogger:
    """ This is multiprocessing safe logger. It should be used by all components in the SDS.

    """

    lock = multiprocessing.RLock()
    levels = {'INFO':             0,
              'DEBUG':           10,
              'WARNING':         20,
              'CRITICAL':        30,
              'EXCEPTION':       40,
              'ERROR':           50,
              'SYSTEM-LOG': 60,
              }

    def __init__(self, stdout_log_level='ERROR', stdout=True, file_log_level='ERROR', output_dir=None):
        self.stdout_log_level = stdout_log_level
        self.stdout = stdout
        self.file_log_level = stdout_log_level
        self.output_dir = output_dir

        self.current_session_log_dir_name = multiprocessing.Array('c', ' ' * 1000)
        self.current_session_log_dir_name.value = ''

    def __repr__(self):
        return "SystemLogger(stdout_log_level='%s', stdout=%s, file_log_level='%s', output_dir=%s)" % \
            (self.stdout_log_level, self.stdout, self.file_log_level, self.output_dir)

    @global_lock(lock)
    def get_time_str(self):
        """ Return current time in ISO format.

        It is useful when constricting file and directory names.
        """
        dt = datetime.now().isoformat('-').replace(':', '-')
        dt += "-" + time.tzname[time.localtime().tm_isdst]

        return dt

    @global_lock(lock)
    def session_start(self, remote_uri):
        """ Create a specific directory for logging a specific call.

        NOTE: This is not completely safe. It can be called from several processes.
        """
        session_name = self.get_time_str() + '-' + remote_uri
        self.current_session_log_dir_name.value = os.path.join(self.output_dir, session_name)
        os.makedirs(self.current_session_log_dir_name.value)

    @global_lock(lock)
    def session_end(self):
        """ Disable logging into the call specific directory
        """
        self.current_session_log_dir_name.value = ''

    @global_lock(lock)
    def get_session_dir_name(self):
        """ Return directory where all the call related files should be stored.
        """
        if self.current_session_log_dir_name.value:
            return self.current_session_log_dir_name.value

        # back off to the default logging directory
        return self.output_dir

    @global_lock(lock)
    def formatter(self, lvl, message):
        """ Format the message - pretty print
        """
        s = self.get_time_str()
        s += '  %-10s : ' % multiprocessing.current_process().name
        s += '%-10s ' % lvl
        s += '\n'

        ss = '    ' + str(message)
        ss = re.sub(r'\n', '\n    ', ss)

        return s + ss + '\n'

    @global_lock(lock)
    def log(self, lvl, message, session_system_log = False):
        """ Log the message based on its level and the logging setting.
        Before writing into a logging file it locks the file.
        """
        if self.stdout:
            # log to stdout
            if SystemLogger.levels[lvl] <= SystemLogger.levels[self.stdout_log_level]:
                print self.formatter(lvl, message)
                sys.stdout.flush()

        if self.output_dir:
            if SystemLogger.levels[lvl] <= SystemLogger.levels[self.file_log_level]:
                # log to the global log
                f = open(os.path.join(self.output_dir, 'system.log'), "a+", 0)
                fcntl.lockf(f, fcntl.LOCK_EX)
                f.write(self.formatter(lvl, message))
                f.write('\n')
                fcntl.lockf(f, fcntl.LOCK_UN)
                f.close()

        if self.current_session_log_dir_name.value:
            if session_system_log or SystemLogger.levels[lvl] <= SystemLogger.levels[self.file_log_level]:
                # log to the call specific log
                f = open(os.path.join(self.current_session_log_dir_name.value, 'system.log'), "a+", 0)
                fcntl.lockf(f, fcntl.LOCK_EX)
                f.write(self.formatter(lvl, message))
                f.write('\n')
                fcntl.lockf(f, fcntl.LOCK_UN)
                f.close()

    @global_lock(lock)
    def info(self, message):
        self.log('INFO', message)

    @global_lock(lock)
    def debug(self, message):
        self.log('DEBUG', message)

    @global_lock(lock)
    def warning(self, message):
        self.log('WARNING', message)

    @global_lock(lock)
    def critical(self, message):
        self.log('CRITICAL', message)

    @global_lock(lock)
    def exception(self, message):
        self.log('EXCEPTION', message)

    @global_lock(lock)
    def error(self, message):
        self.log('ERROR', message)

    @global_lock(lock)
    def session_system_log(self, message):
        """This logs specifically only into call specific system log."""
        self.log('SYSTEM-LOG', message, session_system_log = True)
