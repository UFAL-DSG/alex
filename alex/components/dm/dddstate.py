#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from collections import defaultdict
from copy import deepcopy

from alex.components.dm.base import DiscreteValue, DialogueState
from alex.components.dm.exceptions import DeterministicDiscriminativeDialogueStateException
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActNBList, DialogueActConfusionNetwork


class D3DiscreteValue(DiscreteValue):
    """ This is a simple implementation of probabilistic slot. It serves for the case of simple MDP approach or
     UFAL DSTC 1.0 like dialogue state deterministic update.

    """

    def __init__(self, values={}, name="", desc=""):
        self.name = name
        self.desc = desc

        if values:
            self.values = defaultdict(float, values)
        else:
            self.values = defaultdict(float, {'none': 1.0, })

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __repr__(self):
        return repr(self.values)

    def __unicode__(self):
        return repr(self.values)

    def __getitem__(self, value):
        return self.values[value]

    def __iter__(self):
        return self.values.__iter__()

    def items(self):
        return sorted(self.values.items(), key=lambda x: x[1])

    def reset(self):
        self.values = defaultdict(float, {'none': 1.0, })

    def set(self, value, prob = None):
        """This function sets a probability of a specific value.

        *WARNING* This can lead to un-normalised probabilities.
        """
        if isinstance(value, dict) and not prob:
            # rewrite the complete set of values
            self.values = defaultdict(float, value)
        elif isinstance(value, basestring) and isinstance(prob, float):
            self.values[value] = prob
        else:
            raise DeterministicDiscriminativeDialogueStateException('Unsupported D3DiscreteValue set value.')

    def normalise(self):
        """This function normalises the sum of all probabilities to 1.0"""

        s = sum([v for v in self.values.itervalues()])
        if s < 1e-10:
            # this is a backup solution with unknown consequences
            self.values['none'] = 1.0
        else:
            for value, prob in self.values:
                self.values[value] /= s

    def scale(self, weight):
        """This function scales each probability by the weight"""

        for value, prob in self.values:
            self.values[value] /= weight

    def add(self, value, prob):
        """This function adds a value and its probability"""

        self.values[value] += prob

    def get_most_probable_hyp(self):
        """The function returns the most probable value and its probability
        in a tuple.
        """

        max_prob = -1.0
        max_value = None
        for value, prob in self.values.iteritems():
            if prob >= max_prob:
                max_prob = prob
                max_value = value

        return (max_prob, max_value)

    def get_two_most_probable_hyps(self):
        """This function returns two most probable values and their probabilities.

        The function returns a tuple consisting of two tuples (probability, value).
        """

        max_prob1 = -1.0
        max_value1 = None
        max_prob2 = -1.0
        max_value2 = None

        for value, prob in self.values.iteritems():
            if prob > max_prob1:
                max_prob2, max_prob1 = max_prob1, prob
                max_value2, max_value1 = max_value1, value
            elif prob > max_prob2:
                max_prob2 = prob
                max_value2 = value

        return ((max_prob1, max_value1), (max_prob2, max_value2))

    def test_most_probable_value(self, test_value, test_prob, neg_val=False, neg_prob=False):
        prob, value = self.get_most_probable_hyp()

        if not neg_val:
            if test_value and value != test_value:
                return False
        else:
            if test_value and value == test_value:
                return False

        if not neg_prob:
            if test_prob and prob < test_prob:
                return False
        else:
            if test_prob and prob >= test_prob:
                return False

        return True

    def explain(self, full=False, linear_prob=True):
        """This function prints the values and their probabilities for this node.
        """
        pass


class DeterministicDiscriminativeDialogueState(DialogueState):
    """This is a trivial implementation of a dialogue state and its update.

    It uses only the best dialogue act from the input.
    Based on this it updates its state.
    """

    def __init__(self, cfg, ontology):
        super(DeterministicDiscriminativeDialogueState, self).__init__(cfg, ontology)

        self.slots = defaultdict(D3DiscreteValue)
        self.turns = []
        self.turn_number = 0
        self.debug = cfg['DM']['basic']['debug']
        self.type = cfg['DM']['DeterministicDiscriminativeDialogueState']['type']
        self.session_logger = cfg['Logging']['session_logger']
        self.system_logger = cfg['Logging']['system_logger']

    def __unicode__(self):
        """Get the content of the dialogue state in a human readable form."""
        s = []
        s.append("D3State - Dialogue state content:")
        s.append("")
        s.append("{slot:20} = {value}".format(slot="ludait",value=self.slots["ludait"].items()))

        for name in [sl for sl in sorted(self.slots) if not sl.startswith('ch_') and
                not sl.startswith('sh_') and not sl.startswith('rh_') and
                not sl.startswith("ludait") and isinstance(self.slots[sl], D3DiscreteValue)]:
            s.append("{slot:20} = {value}".format(slot=name,value=self.slots[name].items()))
        s.append("")

        for name in [sl for sl in sorted(self.slots) if sl.startswith('rh_')]:
            s.append("{slot:20} = {value}".format(slot=name,value=self.slots[name].items()))
        s.append("")

        for name in [sl for sl in sorted(self.slots) if sl.startswith('ch_')]:
            s.append("{slot:20} = {value}".format(slot=name,value=self.slots[name].items()))
        s.append("")

        for name in [sl for sl in sorted(self.slots) if sl.startswith('sh_')]:
            s.append("{slot:20} = {value}".format(slot=name,value=self.slots[name].items()))
        s.append("")

        for name in [sl for sl in sorted(self.slots) if not isinstance(self.slots[sl], D3DiscreteValue)]:
            s.append("{slot:20} = {value}".format(slot=name,value=self.slots[name]))

        s.append("")

        return '\n'.join(s)

    def __getitem__(self, key):
        return self.slots[key]

    def __setitem__(self, key, value):
        self.slots[key] = value

    def __contains__(self, key):
        return key in self.slots

    def log_state(self):
        """Log the state using the the session logger."""

        state = []

        state.append(("ludait", self.slots["ludait"]))

        for name in [sl for sl in sorted(self.slots) if not sl.startswith('ch_') and
                not sl.startswith('sh_') and not sl.startswith('rh_') and
                not sl.startswith("ludait")]:
            state.append((name, self.slots[name]))

        for name in [sl for sl in sorted(self.slots) if sl.startswith('rh_')]:
            state.append((name, self.slots[name]))

        for name in [sl for sl in sorted(self.slots) if sl.startswith('ch_')]:
            state.append((name, self.slots[name]))

        for name in [sl for sl in sorted(self.slots) if sl.startswith('sh_')]:
            state.append((name, self.slots[name]))

        self.session_logger.dialogue_state("system", [state, ])

    def restart(self):
        """Reinitialise the dialogue state so that the dialogue manager
        can start from scratch.

        Nevertheless, remember the turn history.
        """

        self.slots = defaultdict(D3DiscreteValue)

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

        if system_da == "silence()":
            # use the last non-silence dialogue act
            # if the system said nothing the last time, lets assume that the
            # user acts in the context of the previous dialogue act
            system_da = self.last_system_da
        else:
            # save the last non-silence dialogue act
            self.last_system_da = system_da

        #if isinstance(user_da, DialogueAct):
        #    # use da as it is
        #    da = user_da
        #elif isinstance(user_da, DialogueActNBList) or isinstance(user_da, DialogueActConfusionNetwork):
        #    # get only the best dialogue act
        #    da = user_da.get_best_da()
        #    # in DSTC baseline like approach I will dais conf. score, so I will not
        #    # have to pick the best hyp
        #    #da = user_da.get_best_nonnull_da()
        #else:
        if not isinstance(user_da, DialogueActConfusionNetwork):
            raise DeterministicDiscriminativeDialogueStateException("Unsupported input for the dialogue manager.")

        if self.debug:
            self.system_logger.debug('D3State Dialogue Act in:\n%s' % user_da)

        # perform the context resolution
        user_da = self.context_resolution(user_da, system_da)

        if self.debug:
            self.system_logger.debug('Context Resolution - Dialogue Act: \n%s' % user_da)

        # perform the state update
        self.state_update(user_da, system_da)
        self.turn_number += 1

        # store the result
        self.turns.append([deepcopy(user_da), deepcopy(system_da), deepcopy(self.slots)])

        # print the dialogue state if requested
        if self.debug:
            self.system_logger.debug(unicode(self))

    def context_resolution(self, user_da, system_da):
        """Resolves and converts meaning of some user dialogue acts
        given the context."""
        new_user_da = DialogueActConfusionNetwork()

        if isinstance(system_da, DialogueAct):
            for system_dai in system_da:
                for prob, user_dai in user_da:
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
                                    user_dai.dat == "affirm" and self.ontology.slot_is_binary(system_dai.name):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "true")

                    elif system_dai.dat == "request" and system_dai.name != "" and \
                                    user_dai.dat == "negate" and self.ontology.slot_is_binary(system_dai.name):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "false")

                    if new_user_dai:
                        new_user_da.add_merge(prob, new_user_dai, 'new')

        new_user_da.extend(user_da)

        return new_user_da

    def state_update(self, user_da, system_da):
        """Records the information provided by the system and/or by the user."""

        # since there is a state update, the silence_time from the last from the user voice activity is 0.0
        # unless this update fired just to inform about the silence time. This case is taken care of later.
        # - this slot is not probabilistic
        self.slots['silence_time'] = 0.0

        # first process the system dialogue act since it was produce "earlier"
        if isinstance(system_da, DialogueAct):
            for dai in system_da:
                if dai.dat == "inform":
                    # set that the system already informed about the slot
                    self.slots["rh_" + dai.name].set({"system-informed": 1.0,})
                    self.slots["ch_" + dai.name].set({"system-informed": 1.0,})
                    self.slots["sh_" + dai.name].set({"system-informed": 1.0,})

                if dai.dat == "iconfirm":
                    # set that the system already informed about the slot
                    self.slots["rh_" + dai.name].set({"system-informed": 1.0,})
                    self.slots["ch_" + dai.name].set({"system-informed": 1.0,})
                    self.slots["sh_" + dai.name].set({"system-informed": 1.0,})

        # now process the user dialogue act
        for prob, dai in user_da:
            #print "#1 SType:", dai.dat, dai.name
            #print "#51", self.slots

            if self.type == "MDP" and prob >= 0.5:
                if dai.dat == "inform":
                    if dai.name:
                        self.slots[dai.name].set({dai.value: 1.0,})
                elif dai.dat == "deny":
                    # handle true and false values because we know their opposite values
                    if dai.value == "true" and self.ontology.slot_is_binary(dai.name):
                        self.slots[dai.name].set({'false': 1.0,})
                    elif dai.value == "false" and self.ontology.slot_is_binary(dai.name):
                        self.slots[dai.name].set({'true': 1.0,})

                    else:
                    # FIXME: This is broken
                        # gat the probability of the denied value
                        denied_value_prob = self.slots[dai.name][dai.value]
                        # it must be changed since user does not want this value but we do not know for what to change it
                        # therefore we will change it probability to 0.0
                        self.slots[dai.name] = D3DiscreteValue({dai.value: 0.0,})
                elif dai.dat == "request":
                    self.slots["rh_" + dai.name].set({"user-requested": 1.0,})
                elif dai.dat == "confirm":
                    self.slots["ch_" + dai.name].set({dai.value: 1.0,})
                elif dai.dat == "select":
                    self.slots["sh_" + dai.name].set({dai.value: 1.0,})
                elif dai.dat in set(["ack", "apology", "bye", "hangup", "hello", "help", "null", "other",
                                 "repeat", "reqalts", "reqmore", "restart", "thankyou"]):
                    self.slots["ludait"].set({dai.dat: 1.0,})
                elif dai.dat == "silence":
                    self.slots["ludait"].set({dai.dat: 1.0,})
                    if dai.name == "time":
                        self.slots['silence_time'] = float(dai.value)
            else:
                pass

        #print "#52", self.slots

    def get_slots_being_requested(self, req_prob=0.8):
        """Return all slots which are currently being requested by the user along with the correct value."""
        requested_slots = {}

        for slot in self.slots:
            if isinstance(self.slots[slot], D3DiscreteValue) and slot.startswith("rh_"):
                if self.slots[slot]["user-requested"] > req_prob:
                    if slot[3:] in self.slots:
                        requested_slots[slot[3:]] = self.slots[slot[3:]]
                    else:
                        requested_slots[slot[3:]] = "none"

        return requested_slots

    def get_slots_being_confirmed(self, conf_prob=0.8):
        """Return all slots which are currently being confirmed by the user along with the value being confirmed."""
        confirmed_slots = {}

        for slot in self.slots:
            if isinstance(self.slots[slot], D3DiscreteValue) and slot.startswith("ch_"):
                prob, value = self.slots[slot].get_most_probable_hyp()
                if value not in ['none', 'system-informed', None] and prob > conf_prob:
                    confirmed_slots[slot[3:]] = self.slots[slot]

        return confirmed_slots

    def get_slots_being_noninformed(self, noninf_prob=0.8):
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
        noninformed_slots = {}

        for slot in self.slots:
            # ignore some slots
            if any([1.0 for x in ['rh_', 'ch_', 'sh_', "ludait"] if slot.startswith(x)]):
                continue
            if not isinstance(self.slots[slot], D3DiscreteValue):
                continue

            # test whether the slot is not currently requested
            if "rh_" + slot not in self.slots or self.slots["rh_" + slot]["none"] > 0.999:
                prob, value = self.slots[slot].get_most_probable_hyp()
                # test that the nin informed value is an interesting value
                if value not in ['none', None] and prob > noninf_prob:
                    noninformed_slots[slot] = self.slots[slot]

        return noninformed_slots

    def get_accepted_slots(self, acc_prob):
        """Returns all slots which have a probability of a non "none" value larger then some threshold.
        """
        accepted_slots = {}

        for slot in self.slots:
            if isinstance(self.slots[slot], D3DiscreteValue):
                prob, value = self.slots[slot].get_most_probable_hyp()
                if value not in ['none', 'system-informed', None] and prob >= acc_prob:
                    accepted_slots[slot] = self.slots[slot]

        return accepted_slots

    def get_slots_tobe_confirmed(self, min_prob, max_prob):
        """Returns all slots which have a probability of a non "none" value larger then some threshold and still not so
        large to be considered as accepted.
        """
        tobe_confirmed_slots = {}

        for slot in self.slots:
            if isinstance(self.slots[slot], D3DiscreteValue):
                prob, value = self.slots[slot].get_most_probable_hyp()
                if value not in ['none', 'system-informed', None] and min_prob <= prob < max_prob  :
                    tobe_confirmed_slots[slot] = self.slots[slot]

        return tobe_confirmed_slots

    def get_slots_tobe_selected(self, sel_prob):
        """Returns all slots which have a probability of the two most probable non "none" value larger then some threshold.
        """
        tobe_selected_slots = {}

        for slot in self.slots:
            if isinstance(self.slots[slot], D3DiscreteValue):
                (prob1, value1), (prob2, value2) = self.slots[slot].get_two_most_probable_hyps()

                if value1 not in ['none', 'system-informed', None] and prob1 > sel_prob and \
                    value2 not in ['none', 'system-informed', None] and prob2 > sel_prob:
                    tobe_selected_slots[slot] = self.slots[slot]

        return tobe_selected_slots

    def get_changed_slots(self, cha_prob):
        """Returns all slots that has changed from the previous turn. Because the change is determined by change in
        probability for a particular value, the can be vary small changes. Therefore we will report only changes
        for values with probability larger then some threshold.
        """
        changed_slots = {}

        # compare the accepted slots from the previous and the current turn
        if len(self.turns) >= 2:
            cur_slots = self.turns[-1][2]
            prev_slots = self.turns[-2][2]

            for slot in cur_slots:
                if isinstance(cur_slots[slot], D3DiscreteValue):
                    cur_prob, cur_value = cur_slots[slot].get_most_probable_hyp()
                    prev_prob, prev_value = prev_slots[slot].get_most_probable_hyp()

                    if cur_value not in ['none', 'system-informed', None] and cur_prob > cha_prob and \
                        prev_value not in ['none', 'system-informed', None] and prev_prob > cha_prob and \
                        cur_value != prev_value:
                        changed_slots[slot] = cur_slots[slot]

            return changed_slots
        else:
            return {}
