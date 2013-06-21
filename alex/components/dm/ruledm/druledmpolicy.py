#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

import re

from iruleds import RuleDS

from alex.components.slu.da import DialogueAct

DEBUG = False
# DEBUG = True
if DEBUG:
    import alex.utils.pdbonerror


# slot names and values
RH_USER_REQUESTED = "user-requested"
CH_SYSTEM_INFORMED = RH_SYSTEM_INFORMED = "system-informed"
LDA_SLOT = "__lda"
ALTS_SLOT = "__alts"
CHANGES_SLOT = "__changes"
BADSLOT_SLOT = "__badslot"
PLACE_INFORMED_SLOT = "__placeinformed"
SLOT_REQ = "rh"
SLOT_CONFIRM = "ch"


class DRuleDS(RuleDS):
    """Represents the state of the dialog."""

    slots = None

    def __init__(self, slots):
        """Build default state representation.

        Args:
           slots (list): list of slot names
        """
        super(DRuleDS, self).__init__()

        self.slots = slots

        self.user_state = None
        self.user_state_confirm = None
        self.user_state_request = None
        self.da_history = None
        self.changed_slots = None
        self.alternative = None

        self.clear()

    def clear(self):
        self.user_state = dict([(s, None) for s in self.slots])
        self.user_state_confirm = dict([(s, []) for s in self.slots])
        self.user_state_request = dict([(s, None) for s in self.slots])

        self.da_history = []
        self.changed_slots = []
        self.alternative = 0

    def update_user(self, new_values, certainty=1.0):
        """Update the values of the state from the new values.

        Args:
           new_values (dict): dictionary with values for the slots
        """
        for key, value in new_values.items():
            if not type(value) is list:
                # update the user's state
                self.user_state[key] = value
                self.changed_slots.insert(0, key)
            else:
                if self.user_state[key] is None:
                    self.user_state[key] = []
                assert type(self.user_state[key]) is list
                self.user_state[key] += value

    def update_user_request(self, new_values, certainty=1.0):
        for key, value in new_values.items():
            self.user_state_request[key] = value

    def update_user_confirm(self, new_values, certainty=1.0):
        for key, value in new_values.items():
            self.user_state_confirm[key] += value

    def update_user_alternative(self):
        self.alternative += 1

    def get_user_alternative(self):
        return self.alternative

    def new_turn(self):
        """Reset the value of the slot that holds information about
        what has been changed so far and in what order.
        """
        self.changed_slots = []

    def __unicode__(self):
        """Pretty print to string the dialogue state."""
        stateval = {key: val for (key, val) in self.user_state.items()
                    if val is not None}
        vals = str(stateval)
        return vals

    def __str__(self):
        return unicode(self)

    def __getitem__(self, key):
        """Get the value of the given slot.

        Args:
           key (str): slot name
        """
        return self.user_state[key]

    def get(self, key, default=None):
        """Get the value of the given slot.

        Args:
           key (str): slot name
           default: default value if the slot is missing
        """
        return self.user_state.get(key, default)


class DRuleDMPolicy:
    db_cls = lambda cfg: None

    def __init__(self, slots, db_cfg):
        self.db = self.db_cls(db_cfg)
        self.slots = slots
        self.values = self.db.get_possible_values()
        self.ontology_unknown_re = re.compile(r"^.*-([0-9]+)")
        self.debug = False

    def build_query(self, state):
        query = {}
        for slot in self.slots:
            if state.get(slot) is not None:
                query[slot] = state[slot]

        return query

    def query_db(self, state):
        query = self.build_query(state)
        return self.db.get_matching(query)

    def user_has_specified_something(self, state):
        return len(self.build_query(state)) > 0

    def get_interesting_slot(self, state):
        return state[CHANGES_SLOT][0]

    def say_bad_slot(self):
        return DialogueAct("sorry()&badslot()")

    def say_bye(self):
        return DialogueAct("bye()")

    def say_hello(self):
        return DialogueAct("hello()")

    def say_instructions(self):
        return DialogueAct("instructions()")

    def say_nomatch(self):
        return DialogueAct("nomatch()")

    def say_query(self, state):
        query = self.build_query(state)
        act = "&".join(["want(%s=%s)" % (k, v,) for k, v in query.items()])
        return DialogueAct(act)

    def say_canreset(self):
        return DialogueAct("canreset()")

    def say_inform(self, state, rec):
        islot_name = self.get_interesting_slot(state) or self.slots[0]
        if not islot_name in rec:
            islot_name = rec.keys()[0]
        slot_name = 'name'
        return DialogueAct(
            "inform(%s='%s')&inform(%s='%s')" % \
            (slot_name, rec[slot_name], islot_name, rec[islot_name])
        )

    def say_slots(self, state, res0, slots_to_say):
        d_str = []
        for slot in slots_to_say:
            d_str += ["inform(%s='%s')" % (slot, res0.get(slot, 'dontknow'), )]
            state.user_state_request[slot] = True

        return DialogueAct("&".join(d_str))

    def say_notunderstood(self):
        return DialogueAct("notunderstood()")

    def answer_confirm(self, state, res0, slots_to_confirm):
        conflicts = []
        selects = []
        noclues = []
        for slot, slot_value in slots_to_confirm.items():
            state.user_state_confirm[slot] = []

            if not slot in res0:
                noclues += [slot]
            elif not res0[slot].lower() in slot_value:
                conflicts += [slot]
                if len(slot_value) > 1:
                    selects += [(slot, res0[slot], )]

        if len(noclues) > 0:
            return DialogueAct(
                "&".join(["noclue(%s)" % n for n in noclues]))
        elif len(conflicts) == 0:
            if len(selects) == 0:
                return DialogueAct("affirm()")
            else:
                return DialogueAct(
                    "&".join(["confirm(%s=%s)" % (n, v, ) \
                              for n, v in selects]))
        else:
            conf_acts = []
            for conflict in conflicts:
                conf_acts += ["inform(%s='%s')" % (conflict, res0[conflict], )]
            res = DialogueAct("negate()")
            # XXX I understood sorting was not desired.  Substituted with
            # the non-sorting version.
            # res.merge(DialogueAct("&".join(conf_acts)))
            res.extend(conf_acts)
            return res

    def pick_record(self, state, res):
        """Get N-th matching record from the database. N is determined
        on number of times the user asked for an alternative."""
        ndx = state.get_user_alternative()
        if len(res) > ndx:
            return res[ndx]
        elif len(res) > 0:
            return res[0]
        else:
            return None

    def get_slots_to_say(self, state):
        keys = [key for key in state.user_state_request.keys()
                if state.user_state_request[key] is False]

        return keys

    def get_slots_to_confirm(self, state):
        keys = {key: value for key, value in state.user_state_confirm.items()
                if len(state.user_state_confirm[key]) != 0}

        return keys

    def get_da(self, state):
        user_da = state.get_curr_user_da()

        # if it is the first turn, say hello
        if user_da is None:
            return state, self.say_hello()

        # if user said bye, say bye
        if user_da.has_dat("bye"):
            return state, self.say_bye()

        # if user requested restart, clear the state
        if user_da.has_dat("restart"):
            state.clear()

        # if we didn't understand tell him
        if len(user_da) == 0 or user_da.has_dat("null"):
            return state, self.say_notunderstood()

        # if the user hasn't specified anything (i.e. blank filter)
        # tell him what he can do
        if not self.user_has_specified_something(state):
            return state, self.say_instructions()

        # get the best answer by using db
        return self._get_da_db(state, user_da)

    def _get_da_db(self, state, user_da):
        res = self.query_db(state)
        slots_to_say = self.get_slots_to_say(state)
        slots_to_confirm = self.get_slots_to_confirm(state)
        res_da = None

        res0 = self.pick_record(state, res)
        # if nothing matches, tell him
        if res0 is None:
            da = self.say_nomatch()
            # XXX I understood sorting was not desired.  Substituted with
            # the non-sorting version.
            # da.merge(self.say_query(state))
            # da.merge(self.say_canreset())
            da.extend(self.say_query(state).dais)
            da.extend(self.say_canreset().dais)
            return state, da

        if self.debug:
            print "USER DA:", user_da, user_da is not None and len(user_da)
            print "STATE:", state
            print "CNT(RES):", len(res)
            print "RES0:", res0
            print "REQ SLOTS:", slots_to_say

        # if the user requested something, tell him immediatelly
        if len(slots_to_say) > 0:
            if not 'name' in slots_to_say:
                slots_to_say = ['name'] + slots_to_say
            res_da = self.say_slots(state, res0, slots_to_say)
            return state, res_da
        else:
            # if not, be ready to tell him something useful
            slots_to_say = ['name', 'food']
            sink_da = self.say_slots(state, res0, slots_to_say)
            # sink_da.append(DialogueActItem().parse("anythingelse()"))

            # if the user wanted to confirm something, do it
            if len(slots_to_confirm) > 0:
                res_da = self.answer_confirm(state, res0, slots_to_confirm)
                return state, res_da
            else:
                # otherwise tell him something useful we prepared
                return state, sink_da
