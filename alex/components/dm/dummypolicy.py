#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

"""
This is an example implementation of a dummy yet funny dialogue policy.
"""

from alex.components.dm import DialoguePolicy
from alex.components.slu.da import DialogueAct, DialogueActItem


class DummyDialoguePolicy(DialoguePolicy):
    """
    This is a trivial policy just to demonstrate basic functionality of
    a proper DM.
    """

    def __init__(self, cfg, ontology):
        super(DummyDialoguePolicy, self).__init__(cfg, ontology)

        self.das = []
        self.last_system_dialogue_act = None

    def get_da(self, dialogue_state):
        # all slots being requested by the user
        requested_slots = dialogue_state.get_requested_slots()
        # all slots being confirmed by the user
        confirmed_slots = dialogue_state.get_confirmed_slots()
        # all slots which had been supplied by the user but have not been
        # implicitly confirmed
        non_informed_slots = dialogue_state.get_non_informed_slots()

        if len(self.das) == 0:
            # NLG("Thank you for calling. How may I help you?")
            self.last_system_dialogue_act = DialogueAct("hello()&thankyou()")
            dialogue_state.slots["ludait"] = "none"

        elif dialogue_state.slots["ludait"] == "bye":
            # NLG("Goodbye.")
            self.last_system_dialogue_act = DialogueAct("bye()")
            dialogue_state.slots["ludait"] = "none"

        elif dialogue_state.slots["ludait"] == "restart":
            # NLG("Let's start again from scratch. How may I help you?")
            dialogue_state.restart()
            self.last_system_dialogue_act = DialogueAct("restart()&hello()")
            dialogue_state.slots["ludait"] = "none"

        elif dialogue_state.slots["ludait"] == "repeat":
            # NLG - use the last dialogue act
            dialogue_state.slots["ludait"] = "none"

        elif dialogue_state.slots["ludait"] == "reqalts":
            # NLG("There is nothing else in the database.")
            self.last_system_dialogue_act = DialogueAct(
                "deny(alternatives=true")
            dialogue_state.slots["ludait"] = "none"

        elif requested_slots:
            # inform about all requested slots
            self.last_system_dialogue_act = DialogueAct()
            for slot in requested_slots:
                dai = DialogueActItem("inform", slot, requested_slots[slot])
                self.last_system_dialogue_act.append(dai)
                dialogue_state.slots["rh_" + slot] = "none"

        elif confirmed_slots:
            # inform about all slots being confirmed by the user
            self.last_system_dialogue_act = DialogueAct()
            for slot in confirmed_slots:
                if confirmed_slots[slot] == dialogue_state.slots[slot]:
                    # it is as user expected
                    self.last_system_dialogue_act.append(
                        DialogueActItem("affirm"))
                    dai = DialogueActItem("inform", slot,
                                          dialogue_state.slots[slot])
                    self.last_system_dialogue_act.append(dai)
                else:
                    # it is something else to what user expected
                    self.last_system_dialogue_act.append(
                        DialogueActItem("negate"))
                    dai = DialogueActItem("deny", slot,
                                          dialogue_state.slots["ch_" + slot])
                    self.last_system_dialogue_act.append(dai)
                    dai = DialogueActItem("inform", slot,
                                          dialogue_state.slots[slot])
                    self.last_system_dialogue_act.append(dai)

                dialogue_state.slots["ch_" + slot] = "none"
        elif non_informed_slots:
            # implicitly confirm all slots provided but not yet implicitly
            # confirmed
            self.last_system_dialogue_act = DialogueAct()
            self.last_system_dialogue_act.append(DialogueActItem("affirm"))
            for slot in non_informed_slots:
                dai = DialogueActItem("inform", slot, non_informed_slots[slot])
                self.last_system_dialogue_act.append(dai)
        else:
            # NLG("Can I help you with anything else?")
            self.last_system_dialogue_act = DialogueAct("reqmore()")
            dialogue_state.slots["ludait"] = "none"

        # record the system dialogue acts
        self.das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act
