#!/usr/bin/env python
# -*- coding: utf-8 -*-


class DialogueManager(object):
    """This is a base class for a dialogue manager. The purpose of a dialogue manager is to accept input
    in the form dialogue acts and respond again in the form of dialogue acts.

    The dialogue manager should be accept multiple inputs without producing any output and producing
    multiple outputs without any input.

    """

    def __init__(self, cfg):
        self.cfg = cfg

    def new_dialogue(self):
        """Initialise the dialogue manager and makes it ready for a new dialogue conversation."""
        pass

    def da_in(self, da):
        """Receives an input dialogue act or dialogue act list with probabilities or dialogue act confusion network.

        When the dialogue act is received an update of the state is performed.
        """
        pass

    def da_out(self):
        """Produces output dialogue act."""
        pass

    def end_dialogue(self):
        """Ends the dialogue and post-process the data."""

    def get_token(self):
        import urllib2

        token_url = self.cfg['DM'].get('token_url')
        curr_session = self.cfg['Logging']['session_logger'].session_dir_name.value
        if token_url is not None:
            f_token = urllib2.urlopen(token_url.format(curr_session))
            return f_token.read()
        else:
            raise Exception("Please configure token_url DM parameter in config.")

