#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# XXX I suggest renaming this to a non-special module name.  It seems strange
# to me for __init__ to actually define any normal classes or functions.  MK

from alex.utils.exception import AlexException
from alex.components.dm.ontology import Ontology


class DialogueStateException(AlexException):
    pass


class DialogueState(object):
    """This is a trivial implementation of a dialogue state and its update.

    It uses only the best dialogue act from the input and based on this it
    updates its state.

    """

    def __init__(self, cfg, ontology):
        self.cfg = cfg
        self.ontology = ontology

    def __str__(self):
        """Get the content of the dialogue state in a human readable form."""
        pass

    def restart(self):
        """
        Reinitialises the dialogue state so that the dialogue manager can start
        from scratch.

        Nevertheless, remember the turn history.
        """

        self.slots = defaultdict(lambda: "none")

    def update(self, user_da, last_system_da):
        """Interface for the dialogue act update.

        It can process dialogue act, dialogue act N best lists, or dialogue act
        confusion networks.

        :param user_da: Dialogue act to process.
        :type user_da: :class:`~alex.components.slu.da.DialogueAct`,
            :class:`~alex.components.slu.da.DialogueActNBList` or
            :class:`~alex.components.slu.da.DialogueActConfusionNetwork`
        :param last_system_da: Last system dialogue act.

        """

    def get_requested_slots(self):
        """
        Returns all slots which are currently being requested by the user along
        with the correct value.
        """
        pass

    def get_confirmed_slots(self):
        """
        Returns all slots which are currently being confirmed by the user along
        with the value being confirmed.
        """
        pass

    def get_non_informed_slots(self):
        """
        Returns all slots provided by the user and the system has not informed
        about them yet along with the value of the slot.
        """
        pass


class DialoguePolicyException(AlexException):
    pass


class DialoguePolicy(object):
    """This is a base class policy. """

    def __init__(self, cfg, ontology):
        self.cfg = cfg
        self.ontology = ontology

    def get_da(self, dialogue_state):
        pass


class DialogueManagerException(AlexException):
    pass


class DialogueManager(object):
    """
    This is a base class for a dialogue manager. The purpose of a dialogue
    manager is to accept input in the form dialogue acts and respond again in
    the form of dialogue acts.

    The dialogue manager should be able to accept multiple inputs without
    producing any output and be able to produce multiple outputs without any
    input.

    """

    def __init__(self, cfg):
        self.cfg = cfg

        self.ontology = Ontology(self.cfg['DM']['ontology'])
        self.dialogue_state_class = self.cfg['DM']['dialogue_state']['type']
        self.dialogue_policy_class = self.cfg['DM']['dialogue_policy']['type']

        self.last_system_dialogue_act = None

        self.new_dialogue()

    def new_dialogue(self):
        """
        Initialises the dialogue manager and makes it ready for a new dialogue
        conversation.
        """

        self.dialogue_state = self.dialogue_state_class(self.cfg,
                                                        self.ontology)
        self.policy = self.dialogue_policy_class(self.cfg, self.ontology)
        self.last_system_dialogue_act = None

    def da_in(self, da, utterance):
        """
        Receives an input dialogue act or dialogue act list with probabilities
        or dialogue act confusion network.

        When the dialogue act is received an update of the state is performed.
        """
        self.dialogue_state.update(da, self.last_system_dialogue_act)

    def da_out(self):
        """Produces output dialogue act."""
        self.last_system_dialogue_act = self.policy.get_da(self.dialogue_state)

        return self.last_system_dialogue_act

    def end_dialogue(self):
        """Ends the dialogue and post-process the data."""
        pass

    def get_token(self):
        import urllib2

        token_url = self.cfg['DM'].get('token_url')
        curr_session = (self.cfg['Logging']['session_logger']
                        .session_dir_name.value)
        if token_url is not None:
            f_token = urllib2.urlopen(token_url.format(curr_session))
            return f_token.read()
        else:
            raise Exception(
                "Please configure the 'token_url' DM parameter in config.")
