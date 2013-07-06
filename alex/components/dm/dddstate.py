#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from collections import defaultdict
from copy import deepcopy

from alex.components.dm.base import DialogueState
from alex.components.dm.exceptions import DeterministicDiscriminativeDialogueStateException
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, DialogueActConfusionNetwork


class DeterministicDiscriminativeDialogueState(DialogueState):
    """This is a trivial implementation of a dialogue state and its update.

    It uses only the best dialogue act from the input.
    Based on this it updates its state.
    """

    def __init__(self, cfg, ontology):
        super(DeterministicDiscriminativeDialogueState, self).__init__(cfg, ontology)

        self.slots = defaultdict(lambda: "none")
        self.turns = []
        self.turn_number = 0

    def __str__(self):
        """Get the content of the dialogue state in a human readable form."""
        s = []
        s.append("DDDState - Dialogue state content:")
        s.append("")
        s.append("%s = %s" % ("ludait", self.slots["ludait"]))

        for name in [sl for sl in sorted(self.slots) if not sl.startswith('ch_') and
                     not sl.startswith('sh_') and not sl.startswith('rh_') and
                     not sl.startswith("ludait")]:
            s.append("%s = %s" % (name, self.slots[name]))
        s.append("")

        for name in [sl for sl in sorted(self.slots) if sl.startswith('rh_')]:
            s.append("%s = %s" % (name, self.slots[name]))
        s.append("")

        for name in [sl for sl in sorted(self.slots) if sl.startswith('ch_')]:
            s.append("%s = %s" % (name, self.slots[name]))
        s.append("")

        for name in [sl for sl in sorted(self.slots) if sl.startswith('sh_')]:
            s.append("%s = %s" % (name, self.slots[name]))

        s.append("")

        return '\n'.join(s)

    def __getitem__(self, key):
        return self.slots[key]

    def __setitem__(self, key, value):
        self.slots[key] = value

    def restart(self):
        """Reinitialise the dialogue state so that the dialogue manager can start from scratch.

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

        if last_system_da == "silence()":
            # use the last non-silence dialogue act
            # if the system said nothing the last time, lets assume that the user acts in the context of the previous
            # dialogue act
            last_system_da = self.last_system_da
        else:
            # save the last non-silence dialogue act
            self.last_system_da = last_system_da

        if isinstance(user_da, DialogueAct):
            # use da as it is
            da = user_da
        elif isinstance(user_da, DialogueActNBList) or isinstance(user_da, DialogueActConfusionNetwork):
            # get only the best dialogue act
#            da = user_da.get_best_da()
            # in DSTC baseline like approach I will dais conf. score, so I will not
            # have to pick the best hyp
            da = user_da.get_best_nonnull_da()
        else:
            raise DeterministicDiscriminativeDialogueStateException(
                "Unsupported input for the dialogue manager.")

        if self.cfg['DM']['basic']['debug']:
            self.cfg['Logging']['system_logger'].debug(u'DDDState Dialogue Act in: %s' % da)

        # store the input
        self.turns.append([da, last_system_da, deepcopy(self.slots)])

        # perform the context resolution
        user_da = self.context_resolution(da, last_system_da)

        if self.cfg['DM']['basic']['debug']:
            self.cfg['Logging']['system_logger'].debug(
                u'Context Resolution - Dialogue Act: %s' % user_da)

        # perform the state update
        self.state_update(user_da, last_system_da)
        self.turn_number += 1

        # print the dialogue state if requested
        if self.cfg['DM']['basic']['debug']:
            self.cfg['Logging']['system_logger'].debug(self)

            requested_slots = self.get_requested_slots()
            confirmed_slots = self.get_confirmed_slots()
            non_informed_slots = self.get_non_informed_slots()
#            accepted_slots = self.get_accepted_slots()
#            changed_slots = self.get_changed_slots()

            s = []
            s.append('DDDState')
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

        new_user_da = DialogueAct()

        if isinstance(last_system_da, DialogueAct):
            for system_dai in last_system_da:
                for user_dai in user_da:
                    new_user_dai = None

                    if system_dai.dat == "confirm" and user_dai.dat == "affirm":
                        new_user_dai = DialogueActItem("inform", system_dai.name, system_dai.value)

                    elif system_dai.dat == "confirm" and user_dai.dat == "negate":
                        new_user_dai = DialogueActItem("deny", system_dai.name, system_dai.value)

                    elif system_dai.dat == "request" and user_dai.dat == "inform" and \
                            system_dai.name != "" and user_dai.name == "" and \
                            user_dai.value == "dontcare":
                        new_user_dai = DialogueActItem("inform", system_dai.name, system_dai.value)

                    elif system_dai.dat == "request" and user_dai.dat == "inform" and \
                            system_dai.name != "" and user_dai.name == "" and \
                            self.ontology.slot_has_value(system_dai.name, user_dai.value):
                        new_user_dai = DialogueActItem("inform", system_dai.name, user_dai.value)

                    elif system_dai.dat == "request" and system_dai.name != "" and \
                            user_dai.dat == "affirm" and system_dai.name.startswith("has_"):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "true")

                    elif system_dai.dat == "request" and system_dai.name != "" and \
                            user_dai.dat == "negate" and system_dai.name.startswith("has_"):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "false")

                    elif system_dai.dat == "request" and system_dai.name != "" and \
                            user_dai.dat == "affirm" and system_dai.name.endswith("_allowed"):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "true")

                    elif system_dai.dat == "request" and system_dai.name != "" and \
                            user_dai.dat == "negate" and system_dai.name.endswith("_allowed"):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "false")

                    if new_user_dai:
                        new_user_da.append(new_user_dai)

        new_user_da.extend(user_da)

        return new_user_da

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

                if dai.dat == "iconfirm":
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
                # handle true and false values because we know their opposite values
                if dai.value == "true":
                    self.slots[dai.name] = "false"
                elif dai.value == "false":
                    self.slots[dai.name] = "true"

                if self.slots[dai.name] == dai.value:
                    # it must be changed since user does not want this value but we do not know for what to change it
                    # therefore it will be changed to None
                    self.slots[dai.name] = "none"
                else:
                    # the value of the slot is different. therefore it does not conflict with
                    # the provided information
                    pass
            elif dai.dat == "request":
                self.slots["rh_" + dai.name] = "user-requested"
            elif dai.dat == "confirm":
                self.slots["ch_" + dai.name] = dai.value
            elif dai.dat == "select":
                self.slots["sh_" + dai.name] = dai.value
            elif dai.dat in ["ack", "apology", "bye", "hangup", "hello", "help", "null", "other",
                             "repeat", "reqalts", "reqmore", "restart", "thankyou"]:
                self.slots["ludait"] = dai.dat
            elif dai.dat == "silence":
                self.slots["ludait"] = dai.dat
                if dai.name == "time":
                    self.slots['silence_time'] = float(dai.value)
                else:
                    self.slots['silence_time'] = 0.0

    def get_requested_slots(self):
        """Return all slots which are currently being requested by the user along with the correct value."""
        requested_slots = {}

        for slot in self.slots:
            if slot.startswith("rh_"):
                if self.slots[slot] == "user-requested":
                    if slot[3:] in self.slots:
                        requested_slots[slot[3:]] = self.slots[slot[3:]]
                    else:
                        requested_slots[slot[3:]] = "none"

        return requested_slots

    def get_confirmed_slots(self):
        """Return all slots which are currently being confirmed by the user along with the value being confirmed."""
        confirmed_slots = {}

        for slot in self.slots:
            if slot.startswith("ch_") and self.slots[slot] != "none" and self.slots[slot] != "system-informed":
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
            if any([1.0 for x in ['rh_', 'ch_', 'sh_', "ludait"] if slot.startswith(x)]):
                continue

            if self.slots[slot] != "none" and ("rh_" + slot not in self.slots or self.slots["rh_" + slot] == "none"):
                non_informed_slots[slot] = self.slots[slot]

        return non_informed_slots

    def get_accepted_slots(self):
        """Returns all slots which has a probability of a non "none" vale larger then some threshold.
        """
        pass

    def get_changed_slots(self):
        """Returns all slots that has changed from the previous turn. Because the change is determined by change in
        probability for a particular value, the can be vary small changes. Therefore we will report only changes
        in accepted slots.
        """

        # compare the accepted slots from the previous and the current turn
        pass
