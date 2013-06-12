#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time

import autopath

from alex.components.dm import DialoguePolicyException, DialoguePolicy
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActConfusionNetwork
from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceConfusionNetwork

from .directions import *

ontology = \
{
'slots':
    {
    },
'slot_atributes':
    {
    'from_stop': ['user_informs',
                  'user_requests',
                  'user_conforms',
                  'system_informs',
                  'system_requests',
                  'system_confirms',
                  'system_selects'],
    'to_stop':   ['user_informs',
                  'user_requests',
                  'user_conforms',
                  'system_informs',
                  'system_requests',
                  'system_confirms',
                  'system_selects'],
    'time':      ['user_informs',
                  'user_requests',
                  'user_conforms',
                  'system_informs',
                  'system_requests',
                  'system_confirms',
                  'system_selects'],
    },
}

class Ontology(object):
    def __init__(self, cfg):
        self.cfg = cfg

    def __getitem__(self, i):
        return ontology[i]


class AOTBHDCPolicyException(DialoguePolicyException):
    pass

class AOTBHDCPolicy(DialoguePolicy):
    """The handcrafted policy for the AOTB system."""

    def __init__(self, cfg):
        super(AOTBHDCPolicy, self).__init__(cfg)

        self.directions = GooglePIDDirectionsFinder()

        self.das = []
        self.last_system_dialogue_act = None



    def get_da(self, dialogue_state):
        # all slots being requested by a user
        requested_slots = dialogue_state.get_requested_slots()
        # all slots being confirmed by a user
        confirmed_slots = dialogue_state.get_confirmed_slots()
        # all slots which had been supplied by a user however they were not implicitly confirmed
        non_informed_slots = dialogue_state.get_non_informed_slots()

        if dialogue_state.turn_number > self.cfg['AlexOnTheBus']['max_turns']:
            res = DialogueAct('bye()&inform(toolong="True")')
        elif len(self.das) == 0:
            # NLG("Dobrý den. Jak Vám mohu pomoci")
            self.last_system_dialogue_act = DialogueAct("hello()")
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
            for slot in non_informed_slots:
                if 'system_informs' in ontology['slot_atributes'][slot]:
                    dai = DialogueActItem("iconfirm", slot, non_informed_slots[slot])
                    self.last_system_dialogue_act.append(dai)
        else:
            # NLG("Can I help you with anything else?")
            self.last_system_dialogue_act = DialogueAct("reqmore()")
            dialogue_state.slots["lda"] = "None"

        # record the system dialogue acts
        self.das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act


    def da_out(self):
        """Produce output dialogue act."""

        if self.state.turn_number == 0:
            res = DialogueAct("hello()")
            return res
        if self.state.turn_number > self.cfg['AlexOnTheBus']['max_turns']:
            res = DialogueAct('bye()&inform(toolong="True")')
            return res
        if self.state.hello:
            self.state.hello = False
        if self.state.bye:
            self.state.bye = False
            res = DialogueAct("bye()")
            return res
        if self.state.help:
            self.state.help = False
            res = DialogueAct("help()")
            return res
        if self.state.repeat:
            self.state.repeat = False
            res = DialogueAct('irepeat()')
            return res
        if self.state.not_understood:
            self.state.not_understood = False
            res = DialogueAct(u'notunderstood()')
            if self.state.from_stop is None:
                res.append(DialogueActItem("help", "from_stop"))
            elif self.state.to_stop is None:
                res.append(DialogueActItem("help", "to_stop"))

            return res
        else:
            req_das = []
            for slot in ['from_stop', 'to_stop']:
                if self.state.get(slot) is None:
                    req_das.append("request(%s)" % slot)

            iconf_das = []
            print self.state.slot_changes

            for slot_change in self.state.slot_changes:
                iconf_das.append("iconfirm(%s=%s)" % (slot_change.slot, slot_change.to_value, ))
                if slot_change.slot in ["from_stop", "to_stop", "time"]:
                    self.state.alternatives = 0

            if len(iconf_das) > 0:
                iconf_da = DialogueAct("&".join(iconf_das))
            else:
                iconf_da = DialogueAct()

            self.state.slot_changes = []

            if len(req_das) > 0:
                req_da = DialogueAct("&".join(req_das))
                iconf_da.extend(req_da)
                return iconf_da
            else:
                time = self.state.time
                if time is None:
                    time = self.get_default_time()
                else:
                    time_parsed = datetime.datetime.strptime(time, "%H:%M")
                    new_hour = time_parsed.hour
                    if datetime.datetime.now().hour > time_parsed.hour:
                        new_hour = (new_hour + 12) % 24

                    time = "%d:%.2d" % (new_hour, time_parsed.minute)

                self.state.set('directions', self.directions.get_directions(
                    from_stop = self.state.from_stop,
                    to_stop = self.state.to_stop,
                    departure_time = time,
                ))

                directions_da = self.say_directions()

                iconf_da.extend(directions_da)
                return iconf_da




    def say_directions(self):
        """Given the state say current directions."""
        route = self.state.directions.routes[self.state.alternatives]

        leg = route.legs[0]  # only 1 leg should be present in case we have no waypoints

        res = []

        if len(self.state.directions) > 1:
            if self.state.alternatives == 0:
                res.append("inform(alternatives=%d)" % len(self.state.directions))
            res.append("inform(alternative=%d)" % (self.state.alternatives + 1))


        for step_ndx, step in enumerate(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                res.append(u"inform(vehicle=%s)" % step.vehicle)
                res.append(u"inform(line=%s)" % step.line_name)
                res.append(u"inform(go_at=%s)" % step.departure_time.strftime("%H:%M"))
                res.append(u"inform(enter_at=%s)" % step.departure_stop)
                res.append(u"inform(headsign=%s)" % step.headsign)
                res.append(u"inform(exit_at=%s)" % step.arrival_stop)
                res.append(u"inform(transfer='True')")

        res = res[:-1]

        if len(res) == 0:
            res.append(u'apology()')
            res.append(u"inform(from_stop='%s')" % self.state.from_stop)
            res.append(u"inform(to_stop='%s')" % self.state.to_stop)

#        print unicode(res)
#        print [type(x) for x in res]
        res_da = DialogueAct(u"&".join(res))

#        print unicode(res_da)

        return res_da

    def get_default_time(self):
        """Return default value for time."""
        return datetime.datetime.now().strftime("%H:%M")
