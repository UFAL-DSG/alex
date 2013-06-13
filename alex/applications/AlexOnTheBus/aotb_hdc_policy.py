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
    'from_stop': set(['zličín', 'anděl', 'zvonařka', 'malostranské náměstí', 'karlovo náměstí']), 
    'to_stop': set(['zličín', 'anděl', 'zvonařka', 'malostranské náměstí', 'karlovo náměstí']), 
    'time': ['7:00', '8:00', '10:00'], 
    },
    
'slot_attributes':
    {
    'from_stop': ['user_informs',
                  'user_requests',
                  'user_confirms',
                  'system_informs',
                  'system_requests',
                  'system_confirms',
                  'system_iconfirms',
                  'system_selects'],
    'to_stop':   ['user_informs',
                  'user_requests',
                  'user_confirms',
                  'system_informs',
                  'system_requests',
                  'system_confirms',
                  'system_iconfirms',
                  'system_selects'],
    'time':      ['user_informs',
                  'user_requests',
                  'user_confirms',
                  'system_informs',
                  #'system_requests',
                  'system_confirms',
                  'system_iconfirms',
                  'system_selects'],
    },
    
'request_tree': 
    {
    'from_stop'
    }
}

def ontology_system_requests():
    return [slot for slot in ontology['slots'] if 'system_requests' in ontology['slot_attributes'][slot]]
    
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

        res_da = None
        
        if dialogue_state.turn_number > self.cfg['AlexOnTheBus']['max_turns']:
            res_da = DialogueAct('bye()&inform(toolong="True")')
        elif len(self.das) == 0:
            # NLG("Dobrý den. Jak Vám mohu pomoci")
            res_da = DialogueAct("hello()")
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "hello":
            # NLG("Ahoj.")
            res_da = DialogueAct("hello()")
            dialogue_state.slots["lda"] = "None"
            
        elif dialogue_state.slots["lda"] == "bye":
            # NLG("Nashledanou.")
            res_da = DialogueAct("bye()")
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "restart":
            # NLG("Dobře, zančneme znovu. Jak Vám mohu pomoci?")
            dialogue_state.restart()
            res_da = DialogueAct("restart()&hello()")
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "repeat":
            # NLG - use the last dialogue act
            res_da = DialogueAct("irepeat()")
            dialogue_state.slots["lda"] = "None"

        elif dialogue_state.slots["lda"] == "reqalts":
            # NLG("There is nothing else in the database.")
            dialogue_state.slots["lda"] = "None"
            
            if dialogue_state.slots['alternatives'] == "None":
                res_da = DialogueAct('request(from_stop)')
            else:
                dialogue_state.slots['alternatives'] += 1
                dialogue_state.slots['alternatives'] %= \
                    len(dialogue_state.directions) if dialogue_state.directions is not None else 1
                
                res_da = self.get_directions(dialogue_state)
            
        elif requested_slots:
            # inform about all requested slots
            res_da = DialogueAct()
            for slot in requested_slots:
                dai = DialogueActItem("inform", slot, requested_slots[slot])
                res_da.append(dai)
                dialogue_state.slots["rh_"+slot] = "None"

        elif confirmed_slots:
            # inform about all slots being confirmed by the user
            res_da = DialogueAct()
            for slot in confirmed_slots:
                if confirmed_slots[slot] == dialogue_state.slots[slot]:
                    # it is as user expected
                    res_da.append(DialogueActItem("affirm"))
                    dai = DialogueActItem("inform", slot, dialogue_state.slots[slot])
                    res_da.append(dai)
                else:
                    # it is something else to what user expected
                    res_da.append(DialogueActItem("negate"))
                    dai = DialogueActItem("deny", slot, dialogue_state.slots["ch_"+slot])
                    res_da.append(dai)
                    dai = DialogueActItem("inform", slot, dialogue_state.slots[slot])
                    res_da.append(dai)

                dialogue_state.slots["ch_"+slot] = "None"
        else:
            res_da = DialogueAct()
            
            if non_informed_slots:
                iconf_da = DialogueAct()
                # implicitly confirm all slots provided but not yet implicitly confirmed
                for slot in non_informed_slots:
                    if 'system_iconfirms' in ontology['slot_attributes'][slot]:
                        dai = DialogueActItem("iconfirm", slot, non_informed_slots[slot])
                        iconf_da.append(dai)
                    
                res_da.extend(iconf_da)
                
            req_da = DialogueAct()
            for slot in ontology_system_requests():
                if dialogue_state.slots[slot] == "None":
                    dai = DialogueActItem("request", slot)
                    print dai
                    req_da.append(dai)
                    
            res_da.extend(req_da)
            
            if len(req_da) == 0:
                dir_da = self.get_directions(dialogue_state)
                res_da.extend(dir_da)


        if res_da is None:
            res_da = DialogueAct("notunderstood()")
            
            if dialogue_state.slots['from_stop'] == "None":
                res_da.append(DialogueActItem("help", "from_stop"))
            elif dialogue_state.slots['from_stop'] == "None":
                res.append(DialogueActItem("help", "to_stop"))
                
            dialogue_state.slots["lda"] = "None"

        self.last_system_dialogue_act = res_da
        
        # record the system dialogue acts
        self.das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act

    def get_directions(self, dialogue_state):
        
        time = dialogue_state.slots['time']
        if time == "None":
            time = self.get_default_time()
        else:
            time_parsed = datetime.datetime.strptime(time, "%H:%M")
            new_hour = time_parsed.hour
            if datetime.datetime.now().hour > time_parsed.hour:
                new_hour = (new_hour + 12) % 24

            time = "%d:%.2d" % (new_hour, time_parsed.minute)

        dialogue_state.directions = self.directions.get_directions(
            from_stop = dialogue_state.slots['from_stop'],
            to_stop = dialogue_state.slots['to_stop'],
            departure_time = time)

        return self.say_directions(dialogue_state)

    def say_directions(self, dialogue_state):
        """Given the state say current directions."""
        if dialogue_state.slots['alternatives'] == "None":
            dialogue_state.slots['alternatives'] = 0
            
        route = dialogue_state.directions.routes[dialogue_state.slots['alternatives']]

        leg = route.legs[0]  # only 1 leg should be present in case we have no waypoints

        res = []

        if len(dialogue_state.directions) > 1:
            if dialogue_state.slots['alternatives'] == 0:
                res.append("inform(alternatives=%d)" % len(dialogue_state.directions))
            res.append("inform(alternative=%d)" % (dialogue_state.slots['alternatives'] + 1))


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
            res.append(u"inform(from_stop='%s')" % dialogue_state.from_stop)
            res.append(u"inform(to_stop='%s')" % dialogue_state.to_stop)

        res_da = DialogueAct(u"&".join(res))


        return res_da

    def get_default_time(self):
        """Return default value for time."""
        return datetime.datetime.now().strftime("%H:%M")
