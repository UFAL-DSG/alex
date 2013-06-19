import atexit
import readline


class Hub(object):
    """Common functionality for the hubs."""
    hub_type = "Hub"

    def __init__(self, cfg):
        self.cfg = cfg
        self.hub_history_file = cfg[self.hub_type]['history_file']
        self.hub_history_length = cfg[self.hub_type]['history_length']

    def init_readline(self):
        "Initialize the readline functionality to enable console history."
        if self.hub_history_file is not None:
            readline.set_history_length(self.hub_history_length)
            try:
                readline.read_history_file(self.hub_history_file)
            except IOError:
                pass

            atexit.register(readline.write_history_file, self.hub_history_file)

    def write_readline(self):
        if self.hub_history_file is not None:
            try:
                readline.write_history_file(self.hub_history_file)
            except IOError:
                pass
