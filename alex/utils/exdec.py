#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pylint: disable-msg=E1103

import functools

""" These are exception decorator handlers to catch repetitive exceptions
you cannot do anything about but silently ignore.
"""

def catch_ioerror(user_function, msg = ""):
    @functools.wraps(user_function)
    def wrapped(*args, **kwds):
        try:
            return user_function(*args, **kwds)
        except IOError:
            print "#"*120
            print u"Unhandled exception IOError in %s" % (unicode(user_function))
            if msg:
                print msg
            print "#"*120

    return wrapped
