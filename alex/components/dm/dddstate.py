#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from collections import defaultdict
from copy import deepcopy

from alex.components.dm.base import DiscreteValue, DialogueState
from alex.components.dm.exceptions import DeterministicDiscriminativeDialogueStateException
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActConfusionNetwork


class D3DiscreteValue(DiscreteValue):
    """This is a simple implementation of a probabilistic slot. It serves for the case of simple MDP approach or
    UFAL DSTC 1.0-like dialogue state deterministic update.
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
        return unicode(self.items())

    def __getitem__(self, value):
        return self.values[value]

    def get(self, value, default_prob):
        return self.values.get(value, default_prob)

    def __iter__(self):
        return self.values.__iter__()

    def items(self):
        return sorted(self.values.items(), key=lambda x: x[1], reverse=True)

    def topn(self, n=-1):
        """THANH: return top n ordered hypotheses, but not none."""
        if n==-1:
            n=len(self.values)
        ret = []
        i=0
        for v, p in self.items():
            if v is None or v=='none':
                continue
            ret.append((v, p))
            i +=1
            if i>=n:
                break
        return ret

    def reset(self):
        self.values = defaultdict(float, {'none': 1.0, })

    def set(self, value, prob=None):
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
        if s < 1e-9:
            # this is a backup solution with unknown consequences
            n = len(self.values)
            for value in self.values:
                self.values[value] = 1.0 / n
        else:
            for value in self.values:
                self.values[value] /= s

    def scale(self, weight):
        """This function scales each probability by the weigh.t"""

        for value in self.values:
            self.values[value] *= weight

    def add(self, value, prob):
        """This function adds probability to the given value."""

        self.values[value] += prob

    def distribute(self, value, dist_prob):
        """This function distributes a portion of probability mass assigned to the ``value`` to other values
         with a weight ``prob``."""

        value_prob = self.values[value]
        non_value_prob = sum([p for v, p in self.values.iteritems() if v != value])

        # first deny the value proportionally to the denied probability
        self.set(value, (1.0 - dist_prob) * value_prob)

        # second redistribute the denied probability mass to to other values proportionally to their own probability
        # if all other values have probability close to zero, then distribute the probability mass uniformly
        for v in self.values:
            if v != value:
                if non_value_prob > 1e-9:
                    self.add(v, dist_prob * value_prob * self.values[v] / non_value_prob)
                else:
                    self.add(v, dist_prob * value_prob * 1.0 / (len(self.values) - 1))

    def mph(self):
        """The function returns the most probable value and its probability
        in a tuple.
        """

        max_prob = -1.0
        max_value = None
        for value, prob in self.values.iteritems():
            if prob > max_prob or \
               prob == max_prob and (max_value == 'none' or max_value is None):

                max_prob = prob
                max_value = value

        return (max_prob, max_value)

    def tmphs(self):
        """This function returns two most probable values and their probabilities. If there are
        multiple values with the same probability, it prefers non-'none' values.

        The function returns a tuple consisting of two tuples (probability, value).

        :rtype: tuple
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

    def test(self, test_value=None, test_prob=None, neg_val=False, neg_prob=False):
        """ Test the most probable value of the slot whether:

        1. the most probable value is equal to test_value and
        2. its probability is larger the test_prob

        Each of the above tests can be negated when neg_* is set True.

        :param test_value:
        :param test_prob:
        :param neg_val:
        :param neg_prob:
        :return:
        """
        prob, value = self.mph()

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
    slots = None

    def __init__(self, cfg, ontology):
        super(DeterministicDiscriminativeDialogueState, self).__init__(cfg, ontology)

        self.turns = []
        self.turn_number = 0
        self.debug = cfg.getpath('DM/basic/debug', False)
        self.type = cfg['DM']['DeterministicDiscriminativeDialogueState']['type']
        self.session_logger = cfg['Logging']['session_logger']
        self.system_logger = cfg['Logging']['system_logger']
        self.restart()

    def __unicode__(self):
        """Get the content of the dialogue state in a human readable form."""
        s = []
        s.append("D3State - Dialogue state content:")
        s.append("")
        s.append("{slot:20} = {value}".format(slot="ludait", value=unicode(self.slots["ludait"])))

        for name in [sl for sl in sorted(self.slots) if not sl.startswith('ch_') and
                not sl.startswith('sh_') and not sl.startswith('rh_') and not sl.startswith('lta_') and
                not sl.startswith("ludait") and isinstance(self.slots[sl], D3DiscreteValue)]:
            s.append("{slot:20} = {value}".format(slot=name, value=unicode(self.slots[name])))
        s.append("")

        for prefix in ['lta_', 'rh_', 'ch_', 'sh_']:
            for name in [sl for sl in sorted(self.slots) if sl.startswith(prefix)]:
                s.append("{slot:20} = {value}".format(slot=name, value=unicode(self.slots[name])))
            s.append("")

        for name in [sl for sl in sorted(self.slots) if not isinstance(self.slots[sl], D3DiscreteValue)]:
            s.append("{slot:20} = {value}".format(slot=name, value=unicode(self.slots[name])))

        s.append("")

        return '\n'.join(s)

    def __getitem__(self, key):
        return self.slots[key]

    def __delitem__(self, key):
        del self.slots[key]

    def __setitem__(self, key, value):
        self.slots[key] = value

    def __contains__(self, key):
        return key in self.slots

    def __iter__(self):
        return iter(self.slots)

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
        # initialize slots
        self.slots = defaultdict(D3DiscreteValue)
        # initialize other variables
        if 'variables' in self.ontology:
            for var_name in self.ontology['variables']:
                setattr(self, var_name, None)

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

        if not isinstance(user_da, DialogueActConfusionNetwork):
            raise DeterministicDiscriminativeDialogueStateException("Unsupported input for the dialogue manager.")

        if self.debug:
            self.system_logger.debug('D3State Dialogue Act in:\n%s' % user_da)

        user_da = self._resolve_user_da_in_context(user_da, system_da)

        if self.debug:
            self.system_logger.debug('Context Resolution - Dialogue Act: \n%s' % user_da)

        user_da = self._infer_last_talked_about_slots(user_da, system_da)

        if self.debug:
            self.system_logger.debug('Last Talked About Inference - Dialogue Act: \n%s' % user_da)

        # perform the state update
        self._update_state(user_da, system_da)
        self.turn_number += 1

        # store the result
        self.turns.append([deepcopy(user_da), deepcopy(system_da), deepcopy(self.slots)])

        # print the dialogue state if requested
        if self.debug:
            self.system_logger.debug(unicode(self))

    def _resolve_user_da_in_context(self, user_da, system_da):
        """Resolves and converts meaning of some user dialogue acts
        given the context."""
        old_user_da = deepcopy(user_da)
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
                                    user_dai.name in self.ontology['context_resolution'] and \
                                    system_dai.name in self.ontology['context_resolution'][user_dai.name] and \
                                    user_dai.value == "dontcare":
                        new_user_dai = DialogueActItem("inform", system_dai.name, system_dai.value)

                    elif system_dai.dat == "request" and user_dai.dat == "inform" and \
                                    user_dai.name in self.ontology['context_resolution'] and \
                                    system_dai.name in self.ontology['context_resolution'][user_dai.name] and \
                                    self.ontology.slot_has_value(system_dai.name, user_dai.value):
                        new_user_dai = DialogueActItem("inform", system_dai.name, user_dai.value)

                    elif system_dai.dat == "request" and system_dai.name != "" and \
                                    user_dai.dat == "affirm" and self.ontology.slot_is_binary(system_dai.name):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "true")

                    elif system_dai.dat == "request" and system_dai.name != "" and \
                                    user_dai.dat == "negate" and self.ontology.slot_is_binary(system_dai.name):
                        new_user_dai = DialogueActItem("inform", system_dai.name, "false")

                    if new_user_dai:
                        new_user_da.add(prob, new_user_dai)

        old_user_da.merge(new_user_da, combine='max')

        return old_user_da

    def _infer_last_talked_about_slots(self, user_da, system_da):
        """This adds dialogue act items to support inference of the last slots the user talked about."""
        old_user_da = deepcopy(user_da)
        new_user_da = DialogueActConfusionNetwork()

        colliding_slots = {}
        done_slots = set()

        for prob, user_dai in user_da:
            new_user_dais = []
            lta_tsvs = self.ontology.last_talked_about(user_dai.dat, user_dai.name, user_dai.value)

            for name, value in lta_tsvs:
                new_user_dais.append(DialogueActItem("inform", name, value))
                if name in done_slots:
                    if not name in colliding_slots:
                        colliding_slots[name] = set()
                    colliding_slots[name].add(value)
                else:
                    done_slots.add(name)

            if new_user_dais:
                for nudai in new_user_dais:
                    if not nudai in new_user_da:
                        new_user_da.add(prob, nudai)

        # In case of collisions, prefer the current last talked about values if it is one of the colliding values.
        # If there is a collision and the current last talked about value is not among the colliding values, do not
        # consider the colliding DA's at all.
        invalid_das = set()
        for prob, da in set(new_user_da):
            if da.name in colliding_slots and self[da.name].mpv() in colliding_slots[da.name]:
                if not da.value == self[da.name].mpv():
                    invalid_das.add(da)
            elif da.name in colliding_slots:
                invalid_das.add(da)

        for invalid_da in invalid_das:
            new_user_da.remove(invalid_da)

        old_user_da.merge(new_user_da, combine='max')

        return old_user_da

    def _update_state(self, user_da, system_da):
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
                    self.slots["rh_" + dai.name].set({"system-informed": 1.0, })
                    self.slots["ch_" + dai.name].set({"system-informed": 1.0, })
                    self.slots["sh_" + dai.name].set({"system-informed": 1.0, })

                if dai.dat == "iconfirm":
                    # set that the system already informed about the slot
                    self.slots["rh_" + dai.name].set({"system-informed": 1.0, })
                    self.slots["ch_" + dai.name].set({"system-informed": 1.0, })
                    self.slots["sh_" + dai.name].set({"system-informed": 1.0, })

        # now process the user dialogue act
        # processing the low probability DAIs first, emphasize the dialogue acts with high probability
        for prob, dai in sorted(user_da.items()):
            #print "#0 ", self.type
            #print "#1 SType:", prob, dai
            ##print "#51", self.slots

            if self.type == "MDP":
                if prob >= 0.5:
                    weight = 0.0
                else:
                    continue
            else:
                weight = 1.0 - prob

            if dai.dat == "inform":
                if dai.name:
                    self.slots[dai.name].scale(weight)
                    self.slots[dai.name].add(dai.value, prob)
            elif dai.dat == "deny":
                # handle true and false values because we know their opposite values
                if dai.value == "true" and self.ontology.slot_is_binary(dai.name):
                    self.slots[dai.name].scale(weight)
                    self.slots[dai.name].add('false', prob)
                elif dai.value == "false" and self.ontology.slot_is_binary(dai.name):
                    self.slots[dai.name].scale(weight)
                    self.slots[dai.name].add('true', prob)
                else:
                    self.slots[dai.name].distribute(dai.value, prob)
            elif dai.dat == "request":
                self.slots["rh_" + dai.name].scale(weight)
                self.slots["rh_" + dai.name].add("user-requested", prob)
            elif dai.dat == "confirm":
                self.slots["ch_" + dai.name].scale(weight)
                self.slots["ch_" + dai.name].add(dai.value, prob)
            elif dai.dat == "select":
                self.slots["sh_" + dai.name].scale(weight)
                self.slots["sh_" + dai.name].add(dai.value, prob)
            elif dai.dat in set(["ack", "apology", "bye", "hangup", "hello", "help", "null", "other",
                             "repeat", "reqalts", "reqmore", "restart", "thankyou"]):
                self.slots["ludait"].scale(weight)
                self.slots["ludait"].add(dai.dat, prob)
            elif dai.dat == "silence":
                self.slots["ludait"].scale(weight)
                self.slots["ludait"].add(dai.dat, prob)
                if dai.name == "time":
                    self.slots['silence_time'] = float(dai.value)

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
                prob, value = self.slots[slot].mph()
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
            if any([1 for x in ['rh_', 'ch_', 'sh_', "ludait"] if slot.startswith(x)]):
                continue
            if not isinstance(self.slots[slot], D3DiscreteValue):
                continue

            # test whether the slot is not currently requested
            if "rh_" + slot not in self.slots or self.slots["rh_" + slot]["none"] > 0.999:
                prob, value = self.slots[slot].mph()
                # test that the nin informed value is an interesting value
                if value not in ['none', None] and prob > noninf_prob:
                    noninformed_slots[slot] = self.slots[slot]

        return noninformed_slots

    def get_accepted_slots(self, acc_prob):
        """Returns all slots which have a probability of a non "none" value larger then some threshold.
        """
        accepted_slots = {}

        for slot in self.slots:
            if any([1 for x in ['rh_', 'ch_', 'sh_', "ludait"] if slot.startswith(x)]):
                continue
            if not isinstance(self.slots[slot], D3DiscreteValue):
                continue

            prob, value = self.slots[slot].mph()
            if value not in ['none', 'system-informed', None] and prob >= acc_prob:
                accepted_slots[slot] = self.slots[slot]

        return accepted_slots

    def get_slots_tobe_confirmed(self, min_prob, max_prob):
        """Returns all slots which have a probability of a non "none" value larger then some threshold and still not so
        large to be considered as accepted.
        """
        tobe_confirmed_slots = {}

        for slot in self.slots:
            if any([1 for x in ['rh_', 'ch_', 'sh_', "ludait"] if slot.startswith(x)]):
                continue
            if not isinstance(self.slots[slot], D3DiscreteValue):
                continue

            prob, value = self.slots[slot].mph()
            if value not in ['none', 'system-informed', None] and min_prob <= prob and prob < max_prob:
                tobe_confirmed_slots[slot] = self.slots[slot]

        return tobe_confirmed_slots

    def get_slots_tobe_selected(self, sel_prob):
        """Returns all slots which have a probability of the two most probable non "none" value larger then some threshold.
        """
        tobe_selected_slots = {}

        for slot in self.slots:
            if any([1 for x in ['rh_', 'ch_', 'sh_', "ludait"] if slot.startswith(x)]):
                continue
            if not isinstance(self.slots[slot], D3DiscreteValue):
                continue

            (prob1, value1), (prob2, value2) = self.slots[slot].tmphs()

            if value1 not in ['none', 'system-informed', None] and prob1 > sel_prob and \
                value2 not in ['none', 'system-informed', None] and prob2 > sel_prob:
                tobe_selected_slots[slot] = self.slots[slot]

        return tobe_selected_slots

    def get_changed_slots(self, cha_prob):
        """Returns all slots that has changed from the previous turn. Because the change is determined by change in
        probability for a particular value, there may be very small changes. Therefore, this will only report changes
        for values with a probability larger than the given threshold.

        :param cha_prob: minimum current probability of the most probable hypothesis to be reported
        :rtype: dict
        """
        changed_slots = {}

        # compare the accepted slots from the previous and the current turn
        if len(self.turns) >= 2:
            cur_slots = self.turns[-1][2]
            prev_slots = self.turns[-2][2]

            for slot in cur_slots:
                if any([1 for x in ['rh_', 'ch_', 'sh_', "ludait"] if slot.startswith(x)]):
                    continue

                if not isinstance(cur_slots[slot], D3DiscreteValue):
                    continue

                cur_prob, cur_value = cur_slots[slot].mph()
                prev_prob, prev_value = prev_slots[slot].mph()

                if cur_value not in ['none', 'system-informed', None] and cur_prob > cha_prob and \
                    prev_value not in ['system-informed', None] and \
                    cur_value != prev_value:
                    #prev_prob > cha_prob and \ # only the current value must be accepted
                    changed_slots[slot] = cur_slots[slot]

            return changed_slots
        elif len(self.turns) == 1:
            # after the first turn all accepted slots are effectively changed
            return self.get_accepted_slots(cha_prob)
        else:
            return {}

    def has_state_changed(self, cha_prob):
        """Returns a boolean indicating whether the dialogue state changed significantly
        since the last turn. True is returned if at least one slot has at least one value
        whose probability has changed at least by the given threshold since last time.

        :param cha_prob: minimum probability change to be reported
        :rtype: Boolean
        """
        if len(self.turns) >= 2:
            cur_slots = self.turns[-1][2]
            prev_slots = self.turns[-2][2]

            for slot in cur_slots:
                if not isinstance(cur_slots[slot], D3DiscreteValue):
                    continue

                for value, cur_prob in cur_slots[slot].items():
                    if value in ['none', 'system-informed', None]:
                        continue
                    prev_prob = prev_slots[slot].get(value, 0.0)
                    if abs(cur_prob - prev_prob) > cha_prob:
                        return True
        elif len(self.turns) == 1:
            slots = self.turns[-1][2]
            for slot in slots:
                if not isinstance(slots[slot], D3DiscreteValue):
                    continue
                prob, value = slots[slot].mph()
                if value in ['none', 'system-informed', None]:
                    continue
                if prob > cha_prob:
                    return True
            pass
        return False
