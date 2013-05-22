#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Matous Machacek, Lukas Zilka

import autopath

from alex.components.dm import DialogueManager
from alex.components.nlg.template import TemplateNLG
from alex.components.slu.da import DialogueAct, DialogueActConfusionNetwork
import urllib
import datetime
import time
import json


class AOTBState(object):
    """Represents the state of dialogue in AOTB dialogue system."""
    from_stop = None
    to_stop = None
    time = None
    turn_number = 0
    directions = None
    alternatives = 0

    def set(self, slot, value):
        print 'setting', slot, value
        setattr(self, slot, value)

    def get(self, slot):
        return getattr(self, slot)


class AOTBDM(DialogueManager):
    """Transport Directions DM"""

    ILLEGAL_VALUES = set(['[OTHER]'])

    def __init__(self, cfg):
        super(AOTBDM, self).__init__(cfg)

        self.cfg = cfg
        self.state = None  # wait for new_dialogue to intialize it
        self.directions = GooglePIDDirectionsFinder()

    def new_dialogue(self):
        """Initialise the dialogue manager and makes it ready for a new dialogue conversation."""
        self.state = AOTBState()

    def da_in(self, da):
        """Receives an input dialogue act or dialogue act list with probabilities or dialogue act confusion network.
        When the dialogue act is received, an update of the state is performed.
        """

        print "understood:", da.cn
        self.state.turn_number += 1

        processed = set()
        for prob, dai in da.cn:
            print 'processing', prob, dai
            if prob < 0.5:  # don't believe low-probability entries
                break

            # update state
            if (not dai.value in self.ILLEGAL_VALUES) and (not dai.value in processed):
                self.update_state(dai)
                processed.add(dai.value)

    def update_state(self, dai):
        if dai.dat == 'inform':
            self.state.set(dai.name, dai.value)

    def say_directions(self):
        route = self.state.directions.routes[self.state.alternatives]

        leg = route.legs[0]  # only 1 leg should be present in case we have no waypoints

        res = []
        for step in leg.steps:
            if step.travel_mode == step.MODE_TRANSIT:
                res.append("inform(vehicle=%s)" % step.vehicle)
                res.append("inform(line=%s)" % step.line_name)
                res.append("inform(go_at=%s)" % step.departure_time)
                res.append("inform(enter_at=%s)" % step.departure_stop)
                res.append("inform(headsign=%s)" % step.headsign)
                res.append("inform(exit_at=%s)" % step.arrival_stop)

        if len(res) == 0:
            res.append("inform(not_found)")
            res.append("inform(from_stop='%s')" % self.state.from_stop)
            res.append("inform(to_stop='%s')" % self.state.to_stop)

        res_da = DialogueAct("&".join(res))

        print res_da

        return res_da

    def get_default_time(self):
        return datetime.datetime.now().strftime("%H:%M")

    def da_out(self):
        """Produces output dialogue act."""

        if self.state.turn_number == 0:
            res = DialogueAct("hello()")
            return res
        else:
            da_strs = []
            for slot in ['from_stop', 'to_stop']:
                if self.state.get(slot) is None:
                    da_strs.append("request(%s)" % slot)

            if len(da_strs) > 0:
                res = DialogueAct("&".join(da_strs))
                return res
            else:
                self.state.set('directions', self.directions.get_directions(
                    from_stop = self.state.from_stop,
                    to_stop = self.state.to_stop,
                    departure_time = self.state.time if self.state.time is not None else self.get_default_time(),
                ))

                directions_da = self.say_directions()
                return directions_da


    def end_dialogue(self):
        """Ends the dialogue and post-process the data."""
        pass

class Directions(object):
    pass

class Route(object):
    pass

class GoogleDirections(Directions):
    def __init__(self, input_json):
        self.routes = []
        for route in input_json['routes']:
            self.routes.append(GoogleRoute(route))

class GoogleRoute(object):
    def __init__(self, input_json):
        self.legs = []
        for leg in input_json['legs']:
            self.legs.append(GoogleRouteLeg(leg))

class GoogleRouteLeg(object):
    def __init__(self, input_json):
        self.steps = []
        for step in input_json['steps']:
            self.steps.append(GoogleRouteLegStep(step))

class GoogleRouteLegStep(object):
    MODE_TRANSIT = "TRANSIT"
    MODE_WALKING = "WALKING"

    def __init__(self, input_json):
        self.travel_mode = input_json['travel_mode']
        if self.travel_mode == self.MODE_TRANSIT:
            self.departure_stop = input_json['transit_details']['departure_stop']['name']
            self.departure_time = input_json['transit_details']['departure_time']['text']
            self.arrival_stop = input_json['transit_details']['arrival_stop']['name']
            self.headsign = input_json['transit_details']['headsign']
            self.vehicle = input_json['transit_details']['line']['vehicle']['type']
            self.line_name = input_json['transit_details']['line']['short_name']





class DirectionsFinder(object):
    def get_directions(self, from_stop, to_stop, time):
        raise NotImplementedException()




class GooglePIDDirectionsFinder(DirectionsFinder):
    def __init__(self, *args, **kwargs):
        super(GooglePIDDirectionsFinder, self).__init__(*args, **kwargs)
        self.directions_url = 'http://maps.googleapis.com/maps/api/directions/json'

    def get_directions(self, from_stop, to_stop, departure_time):
        departure = datetime.datetime.combine(
            datetime.datetime.now(),
            datetime.datetime.strptime(departure_time, "%H:%M").time()
        )

        departure_time = int(time.mktime(departure.timetuple()))

        data = {
            'origin': '%s, Praha' % from_stop.encode('utf8'),
            'destination': '%s, Praha' % to_stop.encode('utf8'),
            'region': 'cz',
            'departure_time': departure_time,
            'sensor': 'false',
            'alternatives': 'true',
            'mode': 'transit',
        }

        page = urllib.urlopen(self.directions_url + '?' + urllib.urlencode(data))
        response = json.load(page)

        directions = GoogleDirections(response)
        return directions


def main():

    cfg = {
      'NLG': {
        'debug': True,
        'type': 'Template',
        'Template' : {
            'model': 'nlg_templates.cfg'
        },
      },
    }
    nlg = TemplateNLG(cfg)
    da = DialogueAct(u'inform(vehicle="TRAM")&inform(line="16")&inform(go_at="4:16pm")&inform(enter_at="Štěpánská")&inform(headsign="Lehovec")&inform(exit_at="Náměstí Míru")')
    print da
    print nlg.generate(da)
    return

    #gpd = GooglePIDDirectionsFinder()
    #route = gpd.get_directions(u"vodičkova", u"hradčanská", "9:00").routes[0]
    #import ipdb; ipdb.set_trace()
    dm = AOTBDM({})
    dm.new_dialogue()
    print dm.da_out()
    #da = DialogueAct(u"inform(from_stop=vodičkova)&inform(to_stop=hradčanská)&inform(time=9:00)")
    da = DialogueAct(u"inform(from_stop=vodičkova)&inform(to_stop=hradčanská)")
    print dm.da_in(DialogueActConfusionNetwork.make_from_da(da))
    print dm.da_out()



if __name__ == '__main__':
    main()