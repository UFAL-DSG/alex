#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __init__ import *


class DeterministicDiscriminativeHandcraftedDM(DialogueManager):
    """This dialogue manager implements
      1) deterministic discriminative dialogue state update
      2) handcrafted dialogue policy

    """

    def __init__(self, cfg):
        self.cfg = cfg

        self.dialogue_state = DeterministicDiscriminativeDialogueState()
        self.policy = HandcraftedPolicy()

    def new_dialogue(self):
        """Initialise the dialogue manager and makes it ready for a new dialogue conversation."""
        pass

    def da_in(self, da):
        """Receives an input dialogue act or dialogue act list with probabilities or dialogue act confusion network.

        When the dialogue act is received, an update of the state is performed.
        """

        self.dialogue_state.update(da)

    def da_out(self):
        """Produces output dialogue act."""

        return self.policy.get_da(self.dialogue_state)

    def end_dialogue(self):
        """Ends the dialogue and post-process the data."""
        pass
