#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
import time
import random

import autopath

from alex.components.dm import DialoguePolicyException, DialoguePolicy
from alex.components.slu.da import DialogueAct, DialogueActItem, DialogueActConfusionNetwork
from alex.components.asr.utterance import Utterance, UtteranceNBList, UtteranceConfusionNetwork

from .directions import *

def randbool(n):
    if random.randint(1, n) == 1:
        return True
        
    return False
    
ontology = \
{
'slots':
    {
    'from_stop': set(['zličín', 'anděl', 'zvonařka', 'malostranské náměstí', 'karlovo náměstí']), 
    'to_stop': set(['zličín', 'anděl', 'zvonařka', 'malostranské náměstí', 'karlovo náměstí']), 
    'time': ['now', '7:00', '8:00', '10:00'], 
    'from_centre': ['dontknow', 'true', 'false'], 
    'to_centre': ['dontknow', 'true', 'false'], 
    },
    
'slot_attributes':
    {
    'from_stop': 
        ['user_informs','user_requests','user_confirms',
         'system_informs','system_requests','system_confirms','system_iconfirms','system_selects'
        ],
    'to_stop':   
        ['user_informs','user_requests','user_confirms',
         'system_informs','system_requests','system_confirms','system_iconfirms','system_selects'
        ],
    'time':
        ['user_informs','user_requests','user_confirms',
         'system_informs',
         #'system_requests',
         'system_confirms','system_iconfirms','system_selects'
        ],
        
    'from_centre':
        ['user_informs','user_requests','user_confirms',
         'system_informs',
         #'system_requests',
         'system_confirms','system_iconfirms','system_selects'
        ],
    'to_centre':  
        ['user_informs','user_requests','user_confirms',
         'system_informs',
         #'system_requests',
         'system_confirms','system_iconfirms','system_selects'
        ],
    'num_transfers':
        [
            'user_requests',
        ],
        
    # not implemented yet
    'transfer_stops':
        [
            'user_requests',
        ],
    'connection_duration':
        [
            'user_requests',
        ],
    'connection_price':
        [
            'user_requests',
        ],

    'connection_time':
        [
            'user_requests',
        ],

    'route_alternative':
        [], 
    },
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
            res_da = DialogueAct('bye()&inform(toolong="true")')
        elif len(self.das) == 0:
            # NLG("Dobrý den. Jak Vám mohu pomoci")
            res_da = DialogueAct("hello()")
            dialogue_state["lda"] = "None"

#       We do not have to reposnd to hello    
#        elif dialogue_state["lda"] == "hello":
#            # NLG("Ahoj.")
#            res_da = DialogueAct("hello()")
#            dialogue_state["lda"] = "None"
            
        elif dialogue_state["lda"] == "bye":
            # NLG("Nashledanou.")
            res_da = DialogueAct("bye()")
            dialogue_state["lda"] = "None"

        elif dialogue_state["lda"] == "help":
            # NLG("Nashledanou.")
            res_da = DialogueAct("help()")
            dialogue_state["lda"] = "None"
            
        elif dialogue_state["lda"] == "thankyou":
            # NLG("Nashledanou.")
            res_da = DialogueAct('inform(cordiality="true")&hello()')
            dialogue_state["lda"] = "None"
            
        elif dialogue_state["lda"] == "restart":
            # NLG("Dobře, zančneme znovu. Jak Vám mohu pomoci?")
            dialogue_state.restart()
            res_da = DialogueAct("restart()&hello()")
            dialogue_state["lda"] = "None"

        elif dialogue_state["lda"] == "repeat":
            # NLG - use the last dialogue act
            res_da = DialogueAct("irepeat()")
            dialogue_state["lda"] = "None"

        elif dialogue_state["lda"] == "reqalts":
            # NLG("There is nothing else in the database.")
            dialogue_state["lda"] = "None"
            
            if dialogue_state['route_alternative'] == "None":
                res_da = DialogueAct('request(from_stop)')
            else:
                dialogue_state['route_alternative'] += 1
                dialogue_state['route_alternative'] %= \
                    len(dialogue_state.directions) if dialogue_state.directions is not None else 1
                
                res_da = self.get_directions(dialogue_state)
            
        elif requested_slots:
            # inform about all requested slots
            res_da = DialogueAct()
            for slot in requested_slots:
                if dialogue_state['route_alternative'] != "None":
                    if slot == "from_stop":
                        res_da.extend(self.get_from_stop(dialogue_state))
                    elif slot == "to_stop":
                        res_da.extend(self.get_to_stop(dialogue_state))
                    elif slot == "num_transfers":
                        res_da.extend(self.get_num_transfers(dialogue_state))
                else:
                    dai = DialogueActItem("inform", slot, requested_slots[slot])
                    res_da.append(dai)
                    dialogue_state["rh_"+slot] = "None"
                    
                dialogue_state["rh_"+slot] = "None"

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
                    dai = DialogueActItem("deny", slot, dialogue_state["ch_"+slot])
                    res_da.append(dai)
                    dai = DialogueActItem("inform", slot, dialogue_state[slot])
                    res_da.append(dai)

                dialogue_state["ch_"+slot] = "None"
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
            if dialogue_state['from_stop'] == "None" or dialogue_state['to_stop'] == "None":
                if dialogue_state['time'] == "None" and randbool(9):
                    req_da.extend(DialogueAct('request(time)'))
                elif dialogue_state['from_centre'] == "None" and dialogue_state['to_centre'] == "None" and randbool(9):
                    if randbool(2):
                        req_da.extend(DialogueAct('confirm(from_centre="true")'))
                    else:
                        req_da.extend(DialogueAct('confirm(to_centre="true")'))
                elif dialogue_state['from_stop'] == "None" and dialogue_state['to_stop'] == "None" and randbool(3):
                    req_da.extend(DialogueAct("request(from_stop)&request(to_stop)"))
                elif dialogue_state['from_stop'] == "None":
                    req_da.extend(DialogueAct("request(from_stop)"))
                elif dialogue_state['to_stop'] == "None":
                    req_da.extend(DialogueAct('request(to_stop)'))
                
            res_da.extend(req_da)
            
            if len(req_da) == 0:
                dir_da = self.get_directions(dialogue_state)
                res_da.extend(dir_da)

        if res_da is None:
            res_da = DialogueAct("notunderstood()")
            
            if dialogue_state['from_stop'] == "None":
                res_da.append(DialogueActItem("help", "from_stop"))
            elif dialogue_state['from_stop'] == "None":
                res.append(DialogueActItem("help", "to_stop"))
                
            dialogue_state["lda"] = "None"

        self.last_system_dialogue_act = res_da
        
        # record the system dialogue acts
        self.das.append(self.last_system_dialogue_act)
        return self.last_system_dialogue_act


    def get_from_stop(self, dialogue_state):
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
                da.append(DialogueActItem('inform', 'arrive_at', step.arrival_time.strftime("%H:%M")))
                
                return da

    def get_num_transfers(self, dialogue_state):
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]
        leg = route.legs[0]
        n = sum([1 for step in leg.steps if step.travel_mode == step.MODE_TRANSIT]) - 1
        da = DialogueAct('inform(num_transfers="%d")' % n)
        return da
        
    def get_directions(self, dialogue_state):
        
        time = dialogue_state['time']
        if time == "None" or time == "now":
            time = self.get_default_time()
        else:
            time_parsed = datetime.datetime.strptime(time, "%H:%M")
            new_hour = time_parsed.hour
            if datetime.datetime.now().hour > time_parsed.hour:
                new_hour = (new_hour + 12) % 24

            time = "%d:%.2d" % (new_hour, time_parsed.minute)

        dialogue_state.directions = self.directions.get_directions(
            from_stop = dialogue_state['from_stop'],
            to_stop = dialogue_state['to_stop'],
            departure_time = time)

        return self.say_directions(dialogue_state)

    def say_directions(self, dialogue_state):
        """Given the state say current directions."""
        if dialogue_state['route_alternative'] == "None":
            dialogue_state['route_alternative'] = 0
            
        route = dialogue_state.directions.routes[dialogue_state['route_alternative']]

        leg = route.legs[0]  # only 1 leg should be present in case we have no waypoints

        res = []

        if len(dialogue_state.directions) > 1:
            if dialogue_state['route_alternative'] == 0:
                res.append("inform(alternatives=%d)" % len(dialogue_state.directions))
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

    def get_default_time(self):
        """Return default value for time."""
        return datetime.datetime.now().strftime("%H:%M")
