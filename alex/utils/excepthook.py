# encoding: utf8
'''
Depending on the hook_type adds various hooks how to catch exceptions
'''
import sys
from alex.utils.exceptions import HookMultipleInstanceException


def ipdb_hook(type, value, tb):
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


def log_hook(type_, value, tb):
    import traceback
    indent = ' ' * 8
    tb_lines = traceback.format_tb(tb)
    tb_msg = ''.join(tb_lines).replace('\n', '\n' + indent)
    msg = '''
    Error occured.
      Type: {type}
      Value: {value}
      Traceback:
        {traceback}'''.format(type=type_, value=value, traceback=tb_msg)
    log(msg)


def log_and_ipdb_hook(type, value, tb):
    log_hook(type, value, tb)
    ipdb_hook(type, value, tb)


def log(msg):
    if ExceptionHook.single is not None:
        ExceptionHook.single._log(msg)


def set_hook(hook_type=None, logger=None):
    try:
        ExceptionHook.single.set_hook(hook_type, logger)
    except:
        raise HookMultipleInstanceException('The singleton instance should be set at startup')


class ExceptionHook(object):
    '''
    Singleton objects for registering various hooks for sys.exepthook.
    For registering a hook, use set_hook.
    '''
    single = None

    def __init__(self, hook_type, logger=None):
        if ExceptionHook.single is not None:
            raise HookMultipleInstanceException(
                "One instance of ExceptionHook has already been created!")
        self.set_hook(hook_type, logger)
        self.logger = logger
        ExceptionHook.single = self

    def _log(self, msg):
        if self.logger is not None:
            # Hardwired debug level. We are debugging, right?
            self.logger.debug(msg)

    def set_hook(self, hook_type=None, logger=None):
        '''Choose an exception hook from predefined functions.

        hook_type: specify the name of the hook method
        '''
        self.logger = logger
        if hook_type is None:
            self._log('Using default OnError.excepthook')
        elif hook_type == 'ipdb':
            sys.excepthook = ipdb_hook
        elif hook_type == 'log':
            sys.excepthook = log_hook
        elif hook_type == 'log_and_ipdb':
            sys.excepthook = log_and_ipdb_hook
        else:
            self._log('Unknown hook_type specified! Keeping the old excepthook!')
