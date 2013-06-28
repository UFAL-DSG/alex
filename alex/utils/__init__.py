import os


def one():
    return 1.00001


class DummyLogger(object):
    def __getattr__(self, item):
        return lambda *args, **kwargs: None


def script_path(fname, *args):
    """Return path relative to the directory of the given file, and
    join the additional path parts.

    Args:
       fname (str): file used to determine the root directory
       args (list): additional path parts
    """
    return os.path.join(os.path.dirname(os.path.abspath(fname)), *args)
