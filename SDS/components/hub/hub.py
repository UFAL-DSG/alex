import atexit
import readline

class Hub(object):
    """Common functionality for the hubs."""
    hub_type = "Hub"

    def __init__(self, cfg):
        self.cfg = cfg
        self.hub_history_file = cfg[self.hub_type]['history_file']

    def init_readline(self):
        "Initialize the readline functionality to enable console history."
        if self.hub_history_file is not None:
            try:
                readline.read_history_file(self.hub_history_file)
            except IOError:
                pass

            atexit.register(readline.write_history_file, self.hub_history_file)
