#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.

import functools
import multiprocessing
import fcntl
import time
import os
import os.path
import sys
import re

from datetime import datetime

"""Implements useful classes for handling multiprocessing implementation of
the alex.

"""


def local_lock():
    """This decorator makes the decorated function thread safe.

    For each function it creates a unique lock.

    """
    lock = multiprocessing.Lock()

    def decorator(user_function):
        @functools.wraps(user_function)
        def wrapper(*args, **kw):
            lock.acquire()
            try:
                return user_function(*args, **kw)
            except Exception as e:
                raise e
            finally:
                lock.release()

        return wrapper

    return decorator


def global_lock(lock):
    """This decorator makes the decorated function thread safe.

    Keyword arguments:
        lock -- an global variable pointing to the object to lock on

    """
    def decorator(user_function):
        @functools.wraps(user_function)
        def wrapper(*args, **kw):
            lock.acquire()
            try:
                return user_function(*args, **kw)
            except Exception as e:
                raise e
            finally:
                lock.release()

        return wrapper

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


class InstanceID(object):
    """ This class provides unique ids to all instances of objects inheriting
    from this class.

    """

    lock = multiprocessing.Lock()
    instance_id = 0

    @global_lock(lock)
    def get_instance_id(self):
        InstanceID.instance_id += 1
        return InstanceID.instance_id


class SystemLogger(object):
    """ This is a multiprocessing safe logger. It should be used by all
    components in the alex.

    """

    lock = multiprocessing.RLock()
    levels = {'INFO':             0,
              'DEBUG':           10,
              'WARNING':         20,
              'CRITICAL':        30,
              'EXCEPTION':       40,
              'ERROR':           50,
              'SYSTEM-LOG':      60,
              }

    def __init__(self, stdout_log_level='ERROR', stdout=True,
                 file_log_level='ERROR', output_dir=None):
        self.stdout_log_level = stdout_log_level
        self.stdout = stdout
        self.file_log_level = stdout_log_level
        self.output_dir = output_dir

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        self.current_session_log_dir_name = multiprocessing.Array(
            'c', ' ' * 1000)
        self.current_session_log_dir_name.value = ''
        self._session_started = False

    def __repr__(self):
        return ("SystemLogger(stdout_log_level='{lvl_out}', stdout={stdout}, "
                "file_log_level='{lvl_f}', output_dir={outdir})").format(
                    lvl_out=self.stdout_log_level, stdout=self.stdout,
                    lvl_f=self.file_log_level, outdir=self.output_dir)

    # XXX: Is the lock any use here?
    @global_lock(lock)
    def get_time_str(self):
        """ Return current time in dashed ISO-like format.

        It is useful in constructing file and directory names.

        """
        # dt = datetime.now().isoformat('-').replace(':', '-')
        # The explicit format seems clearer to me. (Matěj)
        return '{dt}-{tz}'.format(
                    dt=datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f'),
                    tz=time.tzname[time.localtime().tm_isdst])

    @global_lock(lock)
    def session_start(self, remote_uri):
        """ Create a specific directory for logging a specific call.

        NOTE: This is not completely safe. It can be called from several
        processes.

        """
        session_name = self.get_time_str() + '-' + remote_uri
        self.current_session_log_dir_name.value = os.path.join(self.output_dir,
                                                               session_name)
        os.makedirs(self.current_session_log_dir_name.value)
        self._session_started = True

    @global_lock(lock)
    def session_end(self):
        """ Disable logging into the call-specific directory.
        """
        self.current_session_log_dir_name.value = ''
        self._session_started = True

    @global_lock(lock)
    def _get_session_started(self):
        return self._session_started

    session_started = property(_get_session_started)

    # XXX: Returning the enclosing directory in case the session has been
    # closed may not be ideal. In some cases, it causes session logs to be
    # written to outside the related session directory, which is no good.
    @global_lock(lock)
    def get_session_dir_name(self):
        """ Return directory where all the call related files should be stored.
        """
        if self.current_session_log_dir_name.value:
        # This should be equivalent and more accurate. (Matěj)
        # if self._session_started:
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
    def log(self, lvl, message, session_system_log=False):
        """ Log the message based on its level and the logging setting.
        Before writing into a logging file it locks the file.
        """
        if self.stdout:
            # log to stdout
            if SystemLogger.levels[lvl] <= \
                    SystemLogger.levels[self.stdout_log_level]:
                print self.formatter(lvl, message)
                sys.stdout.flush()

        if self.output_dir:
            if SystemLogger.levels[lvl] <= \
                    SystemLogger.levels[self.file_log_level]:
                # log to the global log
                f = open(os.path.join(self.output_dir, 'system.log'), "a+", 0)
                fcntl.lockf(f, fcntl.LOCK_EX)
                f.write(self.formatter(lvl, message))
                f.write('\n')
                fcntl.lockf(f, fcntl.LOCK_UN)
                f.close()

        if self.current_session_log_dir_name.value:
            if (session_system_log
                or SystemLogger.levels[lvl] <= \
                    SystemLogger.levels[self.file_log_level]):
                # log to the call specific log
                f = open(os.path.join(self.current_session_log_dir_name.value,
                                      'system.log'),
                         "a+", 0)
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
        """This logs specifically only into the call-specific system log."""
        self.log('SYSTEM-LOG', message, session_system_log=True)
