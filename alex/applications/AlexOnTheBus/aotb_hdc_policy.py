#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
import random

import autopath

from alex.components.dm import DialoguePolicy
from alex.components.slu.da import DialogueAct, DialogueActItem
# from alex.components.slu.da import DialogueActConfusionNetwork
# from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceConfusionNetwork

from .directions import *


def randbool(n):
    if random.randint(1, n) == 1:
        return True

    return False


class AOTBHDCPolicy(DialoguePolicy):
    """The handcrafted policy for the AOTB system."""

    def __init__(self, cfg, ontology):
        super(AOTBHDCPolicy, self).__init__(cfg, ontology)

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

#        accepted_slots = dialogue_state.get_accepted_slots()
#        changed_slots = dialogue_state.get_changed_slots()

        res_da = None

        if dialogue_state.turn_number > self.cfg['AlexOnTheBus']['max_turns']:
            res_da = DialogueAct('bye()&inform(toolong="true")')
        elif len(self.das) == 0:
            # NLG("Dobrý den. Jak Vám mohu pomoci")
            res_da = DialogueAct("hello()")

#       We do not have to respond to hello
#        elif dialogue_state["ludait"] == "hello":
#            # NLG("Ahoj.")
#            res_da = DialogueAct("hello()")

        elif dialogue_state["ludait"] == "silence":
            # NLG("")
            silence_time = dialogue_state['silence_time']

            if silence_time > self.cfg['DM']['basic']['silence_timeout']:
                res_da = DialogueAct('inform(silence_timeout="true")')
            else:
                res_da = DialogueAct("silence()")

        elif dialogue_state["ludait"] == "bye":
            # NLG("Na shledanou.")
            res_da = DialogueAct("bye()")

        elif dialogue_state["ludait"] == "help":
            # NLG("Pomoc.")
            res_da = DialogueAct("help()")

        elif dialogue_state["ludait"] == "thankyou":
            # NLG("Diky.")
            res_da = DialogueAct('inform(cordiality="true")&hello()')

        elif dialogue_state["ludait"] == "restart":
            # NLG("Dobře, zančneme znovu. Jak Vám mohu pomoci?")
            dialogue_state.restart()
            res_da = DialogueAct("restart()&hello()")

        elif dialogue_state["ludait"] == "repeat":
            # NLG - use the last dialogue act
            res_da = DialogueAct("irepeat()")

        elif dialogue_state["ludait"] == "reqalts":
            # NLG("There is nothing else in the database.")
            # NLG("The next connection is ...")

            if dialogue_state['route_alternative'] == "none":
                res_da = DialogueAct('request(from_stop)')
            else:
                dialogue_state['route_alternative'] += 1
                dialogue_state['route_alternative'] %= \
                    len(dialogue_state.directions) if dialogue_state.directions is not None else 1

                res_da = self.get_directions(dialogue_state)

        elif dialogue_state["alternative"] != "none":
            res_da = DialogueAct()

            if dialogue_state['route_alternative'] != "none":
                if dialogue_state["alternative"] == "last":
                    res_da.extend(self.get_directions(dialogue_state, "last"))
                elif dialogue_state["alternative"] == "next":
                    dialogue_state["route_alternative"] += 1

                    if dialogue_state['route_alternative'] == len(dialogue_state.directions):
                        dialogue_state["route_alternative"] -= 1
                        res_da.append(DialogueActItem("inform", "found_directions", "no_next"))
                    else:
                        res_da.extend(self.get_directions(dialogue_state, "next"))

                elif dialogue_state["alternative"] == "prev":
                    dialogue_state["route_alternative"] -= 1

                    if dialogue_state["route_alternative"] == -1:
                        dialogue_state["route_alternative"] += 1
                        res_da.append(DialogueActItem("inform", "found_directions", "no_prev"))
                    else:
                        res_da.extend(self.get_directions(dialogue_state, "prev"))

                else:
                    dialogue_state["route_alternative"] = int(dialogue_state["alternative"]) - 1
                    res_da.extend(self.get_directions(dialogue_state))

            else:
                res_da.append(DialogueActItem("inform", "stops_conflict", "no_stops"))

            dialogue_state["alternative"] = "none"

        elif requested_slots:
            # inform about all requested slots
            res_da = DialogueAct()
            for slot in requested_slots:
                if dialogue_state['route_alternative'] != "none":
                    if slot == "from_stop":
                        res_da.extend(self.get_from_stop(dialogue_state))
                    elif slot == "to_stop":
                        res_da.extend(self.get_to_stop(dialogue_state))
                    elif slot == "num_transfers":
                        res_da.extend(self.get_num_transfers(dialogue_state))
                else:
                    if slot == "from_stop" or slot == "to_stop" or slot == "num_transfers":
                        dai = DialogueActItem("inform", "stops_conflict", "no_stops")
                        res_da.append(dai)

                        if dialogue_state['from_stop'] == "none":
                            dai = DialogueActItem("help", "inform", "from_stop")
                            res_da.append(dai)
                        elif dialogue_state['to_stop'] == "none":
                            dai = DialogueActItem("help", "inform", "to_stop")
                            res_da.append(dai)
                    else:
                        dai = DialogueActItem("inform", slot, requested_slots[slot])
                        res_da.append(dai)
                        dialogue_state["rh_" + slot] = "none"

                dialogue_state["rh_" + slot] = "none"

        elif confirmed_slots:
            # inform about all slots being confirmed by the user
            res_da = DialogueAct()
            for slot in confirmed_slots:
                if slot == 'XXX':
                    pass
                elif slot == 'XXX':
                    pass
                elif confirmed_slots[slot] == dialogue_state[slot]:
                    # it is as user expected
                    res_da.append(DialogueActItem("affirm"))
                    dai = DialogueActItem("inform", slot, dialogue_state[slot])
                    res_da.append(dai)
                else:
                    # it is something else to what user expected
                    res_da.append(DialogueActItem("negate"))
                    dai = DialogueActItem("deny", slot, dialogue_state["ch_" + slot])
                    res_da.append(dai)

                    if dialogue_state[slot] != "none":
                        dai = DialogueActItem("inform", slot, dialogue_state[slot])

                    res_da.append(dai)

                dialogue_state["ch_" + slot] = "none"

        elif dialogue_state["ludait"] == "other":
            res_da = DialogueAct("notunderstood()")
            res_da.extend(self.get_limited_context_help(dialogue_state))

        else:
            res_da = DialogueAct()

            if non_informed_slots:
                iconf_da = DialogueAct()
                # implicitly confirm all slots provided but not yet implicitly confirmed
                for slot in non_informed_slots:
                    if 'system_iconfirms' in self.ontology['slot_attributes'][slot]:
                        dai = DialogueActItem("iconfirm", slot, non_informed_slots[slot])
                        iconf_da.append(dai)

                res_da.extend(iconf_da)

            req_da = DialogueAct()

            # check all state variables and the output one request dialogue act
            # it just easier to have a list than a tree, the tree is just to confusing for me. FJ
            if dialogue_state['from_stop'] == "none" and dialogue_state['to_stop'] == "none" and \
                dialogue_state['time'] == "none" and \
                randbool(10):
                req_da.extend(DialogueAct('request(time)'))
            elif dialogue_state['from_stop'] == "none" and dialogue_state['from_centre'] == "none" and \
                randbool(9):
                req_da.extend(DialogueAct('confirm(from_centre="true")'))
            elif dialogue_state['to_stop'] == "none" and dialogue_state['to_centre'] == "none" and \
                randbool(8):
                req_da.extend(DialogueAct('confirm(to_centre="true")'))
            elif dialogue_state['from_stop'] == "none" and dialogue_state['to_stop'] == "none" and \
                randbool(3):
                req_da.extend(DialogueAct("request(from_stop)&request(to_stop)"))
            elif dialogue_state['from_stop'] == "none":
                req_da.extend(DialogueAct("request(from_stop)"))
            elif dialogue_state['to_stop'] == "none":
                req_da.extend(DialogueAct('request(to_stop)'))

            res_da.extend(req_da)

            print "X0"
            if len(req_da) == 0:
                print "X1"
                if dialogue_state['from_stop'] == dialogue_state['to_stop']:
                    print "X3"
                    apology_da = DialogueAct()
                    apology_da.extend(DialogueAct(u'apology()'))
                    apology_da.extend(DialogueAct(u'inform(stops_conflict="thesame")'))
                    apology_da.extend(
                        DialogueAct(u"inform(from_stop='%s')" % dialogue_state['from_stop']))
                    apology_da.extend(
                        DialogueAct(u"inform(to_stop='%s')" % dialogue_state['to_stop']))
                    res_da.extend(apology_da)
                else:
                    print "X4"
                    dir_da = self.get_directions(dialogue_state)
                    res_da.extend(dir_da)

        dialogue_state["ludait"] = "none"

        self.last_system_dialogue_act = res_da

        # record the system dialogue acts
        self.das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act

    def get_from_stop(self, dialogue_state):
        """Generates a dialogue act informing about the origin stop of the last recommended connection.

        :rtype : DilogueAct
        """
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'from_stop', step.departure_stop))
                da.append(DialogueActItem('inform', 'vehicle', step.vehicle))
                da.append(DialogueActItem('inform', 'line', step.line_name))
                da.append(DialogueActItem('inform', 'headsign', step.headsign))

                return da

    def get_to_stop(self, dialogue_state):
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        da = DialogueAct()
        for step in reversed(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                da.append(DialogueActItem('inform', 'to_stop', step.arrival_stop))
                da.append(
                    DialogueActItem('inform', 'arrive_at', step.arrival_time.strftime("%H:%M")))

                return da

    def get_num_transfers(self, dialogue_state):
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        n = sum([1 for step in leg.steps if step.travel_mode == step.MODE_TRANSIT]) - 1
        da = DialogueAct('inform(num_transfers="%d")' % n)
        return da

    def get_directions(self, dialogue_state, route_type='true'):

        time = dialogue_state['time']
        if time == "none" or time == "now":
            time = self.get_default_time()
        else:
            time_parsed = datetime.datetime.strptime(time, "%H:%M")
            new_hour = time_parsed.hour
            if datetime.datetime.now().hour > time_parsed.hour:
                new_hour = (new_hour + 12) % 24

            time = "%d:%.2d" % (new_hour, time_parsed.minute)

        dialogue_state.directions = self.directions.get_directions(
            from_stop=dialogue_state['from_stop'],
            to_stop=dialogue_state['to_stop'],
            departure_time=time)

        return self.say_directions(dialogue_state, route_type)

    def say_directions(self, dialogue_state, route_type):
        """Given the state say current directions."""
        if dialogue_state['route_alternative'] == "none":
            dialogue_state['route_alternative'] = 0

        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]

        leg = route.legs[0]  # only 1 leg should be present in case we have no waypoints

        res = []

        if len(dialogue_state.directions) > 1:
            # this is rather annoying since it always finds 4 directions
#                if dialogue_state['route_alternative'] == 0:
#                    res.append("inform(alternatives=%d)" % len(dialogue_state.directions))
            res.append('inform(found_directions="%s")' % route_type)
            if route_type != "last":
                res.append("inform(alternative=%d)" % (dialogue_state['route_alternative'] + 1))

        for step_ndx, step in enumerate(leg.steps):
            if step.travel_mode == step.MODE_TRANSIT:
                res.append(u"inform(vehicle=%s)" % step.vehicle)
                res.append(u"inform(line=%s)" % step.line_name)
                res.append(u"inform(go_at=%s)" % step.departure_time.strftime("%H:%M"))
                res.append(u"inform(enter_at=%s)" % step.departure_stop)
                res.append(u"inform(headsign=%s)" % step.headsign)
                res.append(u"inform(exit_at=%s)" % step.arrival_stop)
                res.append(u"inform(transfer='true')")

        res = res[:-1]

        if len(res) == 0:
            res.append(u'apology()')
            res.append(u"inform(from_stop='%s')" % dialogue_state['from_stop'])
            res.append(u"inform(to_stop='%s')" % dialogue_state['to_stop'])

        res_da = DialogueAct(u"&".join(res))

        return res_da

    def get_limited_context_help(self, dialogue_state):
        res_da = DialogueAct()

        # if we do not understand the input then provide the context sensitive help
        if dialogue_state['route_alternative'] == "none":
            # before something is offered
            if randbool(10):
                res_da.append(DialogueActItem("help", "inform", "hangup"))
            elif randbool(9):
                res_da.append(DialogueActItem("help", "request", "help"))
            elif randbool(8):
                res_da.append(DialogueActItem("help", "inform", "time"))
            elif randbool(7):
                res_da.append(DialogueActItem("help", "repeat"))
            elif dialogue_state['from_stop'] == "none":
                res_da.append(DialogueActItem("help", "inform", "from_stop"))
            elif dialogue_state['to_stop'] == "none":
                res_da.append(DialogueActItem("help", "inform", "to_stop"))
        else:
            # we already offered a connection
            if randbool(4):
                res_da.append(DialogueActItem("help", "inform", "alternative_last"))
            elif randbool(7):
                res_da.append(DialogueActItem("help", "inform", "alternative_next"))
            elif randbool(6):
                res_da.append(DialogueActItem("help", "inform", "alternative_prev"))
            elif randbool(5):
                res_da.append(DialogueActItem("help", "inform", "alternative_abs"))
            elif randbool(4):
                res_da.append(DialogueActItem("help", "request", "from_stop"))
            elif randbool(3):
                res_da.append(DialogueActItem("help", "request", "to_stop"))
            elif randbool(2):
                res_da.append(DialogueActItem("help", "request", "num_transfers"))

        return res_da

    def get_default_time(self):
        """Return default value for time."""
        return datetime.datetime.now().strftime("%H:%M")
