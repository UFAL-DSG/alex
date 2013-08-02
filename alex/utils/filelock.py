# vim: set fileencoding=utf-8
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.
#
"""
Context manager for locking on a file.  Obtained from

    http://www.evanfosmark.com/2009/01
    /cross-platform-file-locking-support-in-python/,

licensed under BSD.

This is thought to work safely on NFS too, in contrast to fcntl.flock().
This is also thought to work safely over SMB and else, in contrast to
fcntl.lockf().  For both issues, consult http://oilq.org/fr/node/13344.

Use as simply as

    with FileLock(filename):
        <critical section for working with the file at `filename'>

"""

from __future__ import unicode_literals

import os
import time
import errno


class FileLockException(Exception):
    pass


class FileLock(object):
    """
    A file locking mechanism that has context-manager support so you can use it
    in a with statement. This should be relatively portable as it doesn't rely
    on msvcrt or fcntl for the locking.

    """

    def __init__(self, file_name, timeout=10, delay=.05):
        """
        Prepare the file locker.  Specify the file to lock and optionally the
        maximum timeout and the delay between each attempt to lock.
        """
        self.is_locked = False
        self.lockfile = os.path.join(os.getcwd(),
                                     "{fname}.lock".format(fname=file_name))
        self.file_name = file_name
        self.timeout = timeout
        self.delay = delay

    def acquire(self):
        """
        Acquire the lock, if possible. If the lock is in use, it check again
        every `wait' seconds. It does this until it either gets the lock or
        exceeds `timeout' number of seconds, in which case it throws an
        exception.

        """
        start_time = time.time()
        while True:
            try:
                self.fd = os.open(self.lockfile,
                                  os.O_CREAT | os.O_EXCL | os.O_RDWR)
                break
            except OSError as er:
                if er.errno != errno.EEXIST:
                    raise er
                if (time.time() - start_time) >= self.timeout:
                    raise FileLockException("Timeout occurred.")
                time.sleep(self.delay)
        self.is_locked = True

    def release(self):
        """
        Get rid of the lock by deleting the lockfile.  When working in a `with'
        statement, this method gets automatically called at the end.

        """
        if self.is_locked:
            # os.close(self.fd)
            # ...Not sure whether we could thus delete a file (on the following
            # line) after having unlocked it.
            os.unlink(self.lockfile)
            self.is_locked = False

    def __enter__(self):
        """
        Activated when used in the `with' statement.  Should automatically
        acquire a lock to be used in the `with' block.

        """
        if not self.is_locked:
            self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        """
        Activated at the end of the with statement.  It automatically releases
        the lock if it is locked.
        """
        if self.is_locked:
            self.release()

    def __del__(self):
        """
        Makes sure that the FileLock instance doesn't leave a lockfile lying
        around.
        """
        self.release()
