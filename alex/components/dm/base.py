#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

from alex.components.dm.ontology import Ontology


class DiscreteValue(object):
    def __init__(self, values, name="", desc=""):
        self.values = values
        self.name = name
        self.desc = desc

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        """Get the content of the dialogue state in a human readable form."""
        pass

    def prune(self, threshold=1e-3):
        """Prune all values with probability less then a threshold."""
        pass

    def normalise(self):
        """This function normalise the sum of all probabilities to 1.0"""
        pass

    def mph(self):
        """The function returns the most probable value and its probability
        in a tuple.
        """
        return None

    def mpv(self):
        """The function returns the most probable value.
        """
        return self.mph()[1]

    def mpvp(self):
        """The function returns the probability of the most probable value.
        """
        return self.mph()[0]

    def tmphs(self):
        """This function returns two most probable values and their probabilities.

        The function returns a tuple consisting of two tuples (probability, value).
        """
        return None

    def tmpvs(self):
        """The function returns two most probable values.
        """
        (prob1, val1), (prob2, val2) = self.tmphs()

        return (val1, val2)

    def tmpvsp(self):
        """The function returns probabilities of two most probable values in the slot.
        """
        (prob1, val1), (prob2, val2) = self.tmphs()

        return (prob1, prob2)

    def explain(self, full=False, linear_prob=False):
        """This function prints the values and their probabilities for this node.
        """
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
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        """Get the content of the dialogue state in a human readable form."""
        pass

    def log_state(self):
        """Log the state using the the session logger."""
        pass

    def restart(self):
        """
        Reinitialises the dialogue state so that the dialogue manager can start
        from scratch.

        Nevertheless, remember the turn history.
        """

        self.slots = defaultdict(lambda: "none")

    def update(self, user_da, system_da):
        """Interface for the dialogue act update.

        It can process dialogue act, dialogue act N best lists, or dialogue act
        confusion networks.

        :param user_da: Dialogue act to process.
        :type user_da: :class:`~alex.components.slu.da.DialogueAct`,
            :class:`~alex.components.slu.da.DialogueActNBList` or
            :class:`~alex.components.slu.da.DialogueActConfusionNetwork`
        :param system_da: Last system dialogue act.

        """

    def get_slots_being_requested(self):
        """
        Returns all slots which are currently being requested by the user along
        with the correct value.
        """
        pass

    def get_slots_being_confirmed(self):
        """
        Returns all slots which are currently being confirmed by the user along
        with the value being confirmed.
        """
        pass

    def get_slots_being_noninformed(self):
        """
        Returns all slots provided by the user and the system has not informed
        about them yet along with the value of the slot.
        """
        pass


class DialoguePolicy(object):
    """This is a base class policy. """

    def __init__(self, cfg, ontology):
        self.cfg = cfg
        self.ontology = ontology

    def get_da(self, dialogue_state):
        pass

    def end_dialogue(self, user_satisfied):
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

        self.dialogue_state = self.dialogue_state_class(self.cfg, self.ontology)
        self.policy = self.dialogue_policy_class(self.cfg, self.ontology)
        self.last_system_dialogue_act = None
        self.user_satisfied = False
        self.in_conversation = True

    def da_in(self, da, utterance=None):
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

    def set_final_reward(self, satisfied):
        self.user_satisfied=satisfied

    def end_dialogue(self):
        """Ends the dialogue and post-process the data."""
        if self.in_conversation:
            self.policy.end_dialogue(self.user_satisfied)
            self.in_conversation = False

    def log_state(self):
        """Log the state of the dialogue state.

        :return: none
        """
        self.dialogue_state.log_state()
