#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.


# Stolen and adapted from
# http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python.
def getTerminalSize():
    """ Retrieves the size of the current terminal window.

    Returns (None, None) in case of lack of success.

    """
    import os
    env = os.environ
    try:
        size = os.popen('stty size', 'r').read().split()
        return int(size[0]), int(size[1])
    except:
        pass

    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            import struct
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
                                                 '1234'))
        except:
            return None
        return cr

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))
    print 'CR: %s' % str(cr)
    return int(cr[1]), int(cr[0])
