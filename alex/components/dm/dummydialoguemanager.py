#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This is an example of implementation of a dialogue manager. It includes a decent implementation
of a dialogue state and a dummy yet funny dialogue policy.
"""
from collections import defaultdict

from alex.components.dm import DialogueManager
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, DialogueActConfusionNetwork
from alex.utils.exception import DummyDialogueManagerException

class DummyDialogueState(object):
    """This is a trivial implementation of a dialogue state and its update.

    It uses only the best dialogue act from the input and based on this it
    updates its state.

    """

    def __init__(self, cfg):
        self.cfg = cfg

        self.slots = defaultdict(lambda: "None")
        self.turns = []

    def __str__(self):
        """Get the content of the dialogue state in a human readable form."""
        s = []
        s.append("DummyDialogueState - Dialogue state content:")
        s.append("")
        for name in sorted(self.slots):
            s.append("%s = %s" % (name, self.slots[name]))
        s.append("")

        return '\n'.join(s)

    def restart(self):
        """Reinitialise the dialogue state so that the dialogue manager can start from scratch.

        Nevertheless, remember the turn history.
        """

        self.slots = defaultdict(lambda: "None")

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

        if isinstance(user_da, DialogueAct):
            # use da as it is
            pass
        elif isinstance(user_da, DialogueActNBList) or isinstance(user_da, DialogueActConfusionNetwork):
            # get only the best dialogue act
            da = user_da.get_best_da()
        else:
            raise DummyDialogueManagerException("Unsupported input for the dialogue manager.")


        if self.cfg['DM']['Dummy']['debug']:
            self.cfg['Logging']['system_logger'].debug('DummyDialogueState Dialogue Act in: %s' % da)

        # store the input
        self.turns.append([da, last_system_da])

        # perform the update
        user_da = self.context_resolution(da, last_system_da)
        self.state_update(da, last_system_da)

        # print the dialogue state if requested
        if self.cfg['DM']['Dummy']['debug']:
            self.cfg['Logging']['system_logger'].debug(self)

            requested_slots = self.get_requested_slots()
            confirmed_slots = self.get_confirmed_slots()
            non_informed_slots = self.get_non_informed_slots()

            s = []
            s.append('DummyDialogueState')
            s.append("")
            s.append("Requested slots:")
            s.append(unicode(requested_slots))
            s.append("Confirmed slots:")
            s.append(unicode(confirmed_slots))
            s.append("Non-informed slots:")
            s.append(unicode(non_informed_slots))
            s = '\n'.join(s)

            self.cfg['Logging']['system_logger'].debug(s)

    def context_resolution(self, user_da, last_system_da):
        """Resolves and converts meaning of some user dialogue acts given the context."""
        if isinstance(last_system_da, DialogueAct):
            for system_dai in user_da:
                for user_dai in user_da:
                    new_user_dai = None

                    if last_system_da.has_only_dat("confirm") and user_dai.dat == "affirm":
                        new_user_dai = DialogueActItem("inform", system_dai.name, system_dai.value)

                    elif last_system_da.has_only_dat("confirm") and user_dai.dat == "negate":
                        new_user_dai = DialogueActItem("deny", last_system_da.name, last_system_da.value)

                    elif last_system_da.has_only_dat("request") and user_dai.dat == "inform" and \
                            user_dai.name == "" and user_dai.value == "dontcare":
                        new_user_dai = DialogueActItem("inform", last_system_da.name, last_system_da.value)

                    elif last_system_da.has_only_dat("request") and user_dai.dat == "affirm" and user_dai.name.startswith("has_"):
                        new_user_dai = DialogueActItem("inform", last_system_da.name, "true")

                    elif last_system_da.has_only_dat("request") and user_dai.dat == "negate" and user_dai.name.startswith("has_"):
                        new_user_dai = DialogueActItem("inform", last_system_da.name, "false")

                    elif last_system_da.has_only_dat("request") and user_dai.dat == "affirm" and user_dai.name.endswith("_allowed"):
                        user_dai = DialogueActItem("inform", last_system_da.name, "true")

                    elif last_system_da.has_only_dat("request") and user_dai.dat == "negate" and user_dai.name.endswith("_allowed"):
                        user_dai = DialogueActItem("inform", last_system_da.name, "false")

                    if new_user_dai:
                        user_da.append(new_user_dai)

        return user_da

    def state_update(self, user_da, last_system_da):
        """Records the information provided by the system and/or by the user."""

        # first process the system dialogue act since it was produce "earlier"
        if isinstance(last_system_da, DialogueAct):
            for dai in last_system_da:
                if dai.dat == "inform":
                    # set that the system already informed about the slot
                    self.slots["rh_" + dai.name] = "system-informed"
                    self.slots["ch_" + dai.name] = "system-informed"
                    self.slots["sh_" + dai.name] = "system-informed"

        # now process the user dialogue act
        for dai in user_da:
            if dai.dat == "inform":
                if dai.name:
                    self.slots[dai.name] = dai.value
            elif dai.dat == "deny":
                if self.slots[dai.name] == dai.value:
                    # it must be changed since user does not want this but we do not know for what to change it
                    # therefore it will be changed to None
                    self.slots[dai.name] = "None"
                else:
                    # the value of the slot is different. therefore it does not conflict with the provided information
                    pass
            elif dai.dat == "request":
                self.slots["rh_" + dai.name] = "user-requested"
            elif dai.dat == "confirm":
                self.slots["ch_" + dai.name] = dai.value
            elif dai.dat == "select":
                self.slots["sh_" + dai.name] = dai.value
            elif dai.dat in ["ack", "apology", "bye", "hangup", "hello", "help", "null",
                             "repeat", "reqalts", "reqmore", "restart", "thankyou"]:
                self.slots["lda"] = dai.dat

    def get_requested_slots(self):
        """Return all slots which are currently being requested by the user along with the correct value."""
        requested_slots = {}

        for slot in self.slots:
            if slot.startswith("rh_"):
                if self.slots[slot] == "user-requested":
                    if slot[3:] in self.slots:
                        requested_slots[slot[3:]] = self.slots[slot[3:]]
                    else:
                        requested_slots[slot[3:]] = "None"

        return requested_slots

    def get_confirmed_slots(self):
        """Return all slots which are currently being confirmed by the user along with the value being confirmed."""
        confirmed_slots = {}

        for slot in self.slots:
            if slot.startswith("ch_") and self.slots[slot] != "None" and self.slots[slot] != "system-informed":
                confirmed_slots[slot[3:]] = self.slots[slot]

        return confirmed_slots

    def get_non_informed_slots(self):
        """Return all slots provided by the user and the system has not informed about them yet along with
        the value of the slot.

        This will not detect a change in a goal. For example::

            U: I want a Chinese restaurant.
            S: Ok, you want a Chinese restaurant. What price range you have in mind?
            U: Well, I would rather want an Italian Restaurant.
            S: Ok, no problem. You want an Italian restaurant. What price range you have in mind?

        Because the system informed about the food type and stored "system-informed", then
        we will not notice that we confirmed a different food type.
        """
        non_informed_slots = {}

        for slot in self.slots:
            # ignore some slots
            if [ 1.0 for x in ['rh_', 'ch_', 'sh_', 'lda'] if slot.startswith(x)]:
                continue

            if self.slots[slot] != "None" and ("rh_"+slot not in self.slots or self.slots["rh_"+slot] == "None"):
                non_informed_slots[slot] = self.slots[slot]

        return non_informed_slots

class DummyPolicy(object):
    """This is a trivial policy just to demonstrate basic functionality of a proper DM."""

    def __init__(self, cfg):
        self.cfg = cfg

        self.das = []
        self.last_system_dialogue_act = None

    def get_da(self, dialogue_state):
        # all slots being requested by a user
        requested_slots = dialogue_state.get_requested_slots()
        # all slots being confirmed by a user
        confirmed_slots = dialogue_state.get_confirmed_slots()
        # all slots which had been supplied by a user however they were not implicitly confirmed
        non_informed_slots = dialogue_state.get_non_informed_slots()

        if len(self.das) == 0:
            # NLG("Thank you for calling. How may I help you?")
            self.last_system_dialogue_act = DialogueAct("thankyou()&hello()")
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "bye":
            # NLG("Goodbye.")
            self.last_system_dialogue_act = DialogueAct("bye()")
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "restart":
            # NLG("Let's start again from scratch. How may I help you?")
            dialogue_state.restart()
            self.last_system_dialogue_act = DialogueAct("restart()&hello()")
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "repeat":
            # NLG - use the last dialogue act
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "reqalts":
            # NLG("There is nothing else in the database.")
            self.last_system_dialogue_act = DialogueAct("deny(alternatives=true")
            dialogue_state.slots["lda"] = "None"

        elif requested_slots:
            # inform about all requested slots
            self.last_system_dialogue_act = DialogueAct()
            for slot in requested_slots:
                dai = DialogueActItem("inform", slot, requested_slots[slot])
                self.last_system_dialogue_act.append(dai)
                dialogue_state.slots["rh_"+slot] = "None"

        elif confirmed_slots:
            # inform about all slots being confirmed by the user
            self.last_system_dialogue_act = DialogueAct()
            for slot in confirmed_slots:
                if confirmed_slots[slot] == dialogue_state.slots[slot]:
                    # it is as user expected
                    self.last_system_dialogue_act.append(DialogueActItem("affirm"))
                    dai = DialogueActItem("inform", slot, dialogue_state.slots[slot])
                    self.last_system_dialogue_act.append(dai)
                else:
                    # it is something else to what user expected
                    self.last_system_dialogue_act.append(DialogueActItem("negate"))
                    dai = DialogueActItem("deny", slot, dialogue_state.slots["ch_"+slot])
                    self.last_system_dialogue_act.append(dai)
                    dai = DialogueActItem("inform", slot, dialogue_state.slots[slot])
                    self.last_system_dialogue_act.append(dai)

                dialogue_state.slots["ch_"+slot] = "None"
        elif non_informed_slots:
            # implicitly confirm all slots provided but not yet implicitly confirmed
            self.last_system_dialogue_act = DialogueAct()
            self.last_system_dialogue_act.append(DialogueActItem("affirm"))
            for slot in non_informed_slots:
                dai = DialogueActItem("inform", slot, non_informed_slots[slot])
                self.last_system_dialogue_act.append(dai)
        else:
            # NLG("Can I help you with anything else?")
            self.last_system_dialogue_act = DialogueAct("reqmore()")
            dialogue_state.slots["lda"] = "None"

        # record the system dialogue acts
        self.das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act


class DummyDM(DialogueManager):
    """This is an example of an dialogue manager. It is fully handcrafted and it has a limited functionality.

    The dialogue state and the dialogue policy are implemented in a very simplistic way.

    The purpose of this class is to serve for debugging and testing of other components when building the
    full dialogue system.

    """

    def __init__(self, cfg):
        self.cfg = cfg

        self.last_system_dialogue_act = None

        self.new_dialogue()

    def new_dialogue(self):
        """Initialise the dialogue manager and makes it ready for a new dialogue conversation."""

        self.dialogue_state = DummyDialogueState(self.cfg)
        self.policy = DummyPolicy(self.cfg)

    def da_in(self, da):
        """Receives an input dialogue act or dialogue act list with probabilities or dialogue act confusion network.

        When the dialogue act is received, an update of the state is performed.
        """

        self.dialogue_state.update(da, self.last_system_dialogue_act)

    def da_out(self):
        """Produces output dialogue act."""

        self.last_system_dialogue_act = self.policy.get_da(self.dialogue_state)

        return self.last_system_dialogue_act

    def end_dialogue(self):
        """Ends the dialogue and post-process the data."""
        pass
