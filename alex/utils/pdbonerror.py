# encoding: utf8
'''
Depending on the behaviour adds various hooks how to catch exceptions
'''

import sys
logger = None


def _log(msg):
    if logger is not None:
        # Hardwired debug level. We are debugging, right?
        logger.debug(msg)


def set_logger(logger=None):
    this_module = sys.modules[__name__]
    setattr(this_module, 'logger', logger)


def ipdb_hook(type, value, tb):
    _log("ipdb_hook exception caught: %s", str(type))
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
    # we are in interactive mode or we don't have a tty-like
    # device, so we call the default hook
        sys.__excepthook__(type, value, tb)
    else:
        import traceback
        import ipdb
        # we are NOT in interactive mode, print the exception…
        traceback.print_exception(type, value, tb)
        print
        # …then start the debugger in post-mortem mode.
        # pdb.pm() # deprecated
        ipdb.post_mortem(tb)  # more “modern”


def rpdb_hook(type, value, tb):
    _log("rpdb_hook exception caught: %s", str(type))
    # _log('Running remote debugger!')
    # import rpdb
    # rpdb.Rpdb().set_trace()
    # FIXME how did Lukas used it?


def set_hook(behaviour=None, logger=None):
    set_logger(logger)
    if behaviour is None:
        _log('Using default OnError.excepthook')
    elif behaviour == 'ipdb':
        sys.excepthook = ipdb_hook
    elif behaviour == 'rpdb':
        sys.excepthook = rpdb_hook
    else:
        _log('Unknown behaviour specified! Keeping the old excepthook!')
