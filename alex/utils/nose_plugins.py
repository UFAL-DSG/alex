import os
import sys

from nose2.events import Plugin


class TestSkipperPlugin(Plugin):
    """Skip tests defined in the nose2.cfg.

    This class exists as a temporary solution until we fix all tests.
    Hopefully we will be able to delete this class soon.
    """
    configSection = 'testskipper'

    def __init__(self, *args, **kwargs):
        super(TestSkipperPlugin, self).__init__(*args, **kwargs)

        # Figure out alex's absolute path so that we can match filenames of the
        # tests with the configured relative paths that we want to skip.
        self.alex_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir)
        )

        # Build a list of absolute paths to be ignored.
        self.ignore_paths = [
            os.path.abspath(
                os.path.join(self.alex_root, p)
            ) for p in self.config.get('ignore_paths').split()]

        for path in self.ignore_paths:
            print >>sys.stderr, 'WARNING: Ignoring path:', path

    def matchPath(self, event):
        """Skip the configured tests."""
        event.handled = True

        for p in self.ignore_paths:
            if event.path.startswith(p):
                return False

        return True