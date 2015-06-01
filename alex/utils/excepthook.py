# encoding: utf8
'''
Depending on the hook_type,
ExceptionHook class adds various hooks how to catch exceptions.
'''
import sys


### Hook functions
# {{{
WEIRD_STUFF_MSG = "BE CAREFUL! Exception happened while executing an " \
                  "exception handler. Weird stuff can happen!"


def hook_decorator(f):
    """Print the caution message when the decorated function raises an error."""

    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception, e:
            import traceback
            print traceback.print_exc()
            print >>sys.stderr, WEIRD_STUFF_MSG
            # Do not raise
    return wrapper


@hook_decorator
def ipdb_hook(type_, value, tb):
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
    # we are in interactive mode or we don't have a tty-like
    # device, so we call the default hook
        sys.__excepthook__(type_, value, tb)
    else:
        import traceback
        import ipdb
        # we are NOT in interactive mode, print the exception…
        traceback.print_exception(type_, value, tb)
        print
        # …then start the debugger in post-mortem mode.
        # pdb.pm() # deprecated
        ipdb.post_mortem(tb)  # more “modern”


@hook_decorator
def log_hook(type_, value, tb):
    import traceback
    indent = ' ' * 8
    tb_lines = traceback.format_tb(tb)
    tb_msg = (''.join(ln.decode('utf8') for ln in tb_lines)
              .replace('\n','\n' + indent))
    msg = u'''
    Error occured.
      Type: {type}
      Value: {value}
      Traceback:
        {traceback}'''.format(type=type_, value=value, traceback=tb_msg)
    ExceptionHook._log(msg)


@hook_decorator
def log_and_ipdb_hook(type_, value, tb):
    log_hook(type_, value, tb)
    ipdb_hook(type_, value, tb)

# }}}


class ExceptionHook(object):
    '''
    Singleton objects for registering various hooks for sys.exepthook.
    For registering a hook, use set_hook.
    '''
    logger = None

    def __init__(self, hook_type, logger=None):
        '''
        Creation of object is dummy operation here.
        By creating and object you just setting
        hook_type and logger.
        The object can be used to store settings for excepthook.
        a = ExceptionHook('log',logger=YourLogger) # now it logs
        b = ExceptionHook('ipdb')  # now it uses ipdb
        a.apply() # now it logs again
        '''
        ExceptionHook.set_hook(hook_type, logger)
        self.hook_type = hook_type
        self.logger = logger

    def apply(self):
        '''
        The object can be used to store settings for excepthook.
        a = ExceptionHook('log') # now it logs
        b = ExceptionHook('ipdb')  # now it uses ipdb
        a.apply() # now it logs again
        '''
        ExceptionHook.set_hook(self.hook_type, self.logger)
        return self

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return '''
        ExceptionHook
          Hook Type: {type}
          Hook Logger: {logger}'''.format(type=self.hook_type, logger=self.logger)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.__str__())

    @classmethod
    def _log(cls, msg):
        if cls.logger is not None:
            # Hardwired debug level. We are debugging, right?
            cls.logger.debug(msg)

    @classmethod
    def set_hook(cls, hook_type=None, logger=None):
        '''Choose an exception hook from predefined functions.

        hook_type: specify the name of the hook method
        '''
        cls.logger = logger
        if (hook_type is None) or (hook_type == 'None') or (hook_type == ''):
            cls._log('Keeping the old excepthook!')
        elif hook_type == 'ipdb':
            sys.excepthook = ipdb_hook
        elif hook_type == 'log':
            sys.excepthook = log_hook
        elif hook_type == 'log_and_ipdb':
            sys.excepthook = log_and_ipdb_hook
        elif hook_type == 'system':
            # Handle an exception by displaying it with a traceback on sys.stderr.
            sys.excepthook = sys.__excepthook__
        else:
            cls._log('''Unknown hook_type: {hook_type}!
                    Keeping the old excepthook!'''.format(hook_type=hook_type))
