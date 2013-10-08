#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
from datetime import datetime
from datetime import time as dttime
import time
import json


class Directions(object):
    pass


class Route(object):
    pass


class GoogleDirections(Directions):
    def __init__(self, input_json):
        self.routes = []
        for route in input_json['routes']:
            self.routes.append(GoogleRoute(route))

    def __len__(self):
        return len(self.routes)

    def __repr__(self):
        ret = ''
        for i, route in enumerate(self.routes, start=1):
            ret += "ROUTE " + str(i) + "\n" + route.__repr__() + "\n\n"
        return ret


class GoogleRoute(Route):
    def __init__(self, input_json):
        self.legs = []
        for leg in input_json['legs']:
            self.legs.append(GoogleRouteLeg(leg))

    def __repr__(self):
        ret = ''
        for i, leg in enumerate(self.legs, start=1):
            ret += "LEG " + str(i) + "\n" + leg.__repr__() + "\n"
        return ret


class GoogleRouteLeg(object):
    def __init__(self, input_json):
        self.steps = []
        for step in input_json['steps']:
            self.steps.append(GoogleRouteLegStep(step))

    def __repr__(self):
        return "\n".join(step.__repr__() for step in self.steps)


class GoogleRouteLegStep(object):
    MODE_TRANSIT = "TRANSIT"
    MODE_WALKING = "WALKING"

    def __init__(self, input_json):
        self.travel_mode = input_json['travel_mode']
        if self.travel_mode == self.MODE_TRANSIT:
            self.departure_stop = \
                    input_json['transit_details']['departure_stop']['name']
            self.departure_time = \
                    self.parsetime(input_json['transit_details']
                                   ['departure_time']['text'])
            self.arrival_stop = \
                    input_json['transit_details']['arrival_stop']['name']
            self.arrival_time = \
                    self.parsetime(input_json['transit_details']
                                   ['arrival_time']['text'])
            self.headsign = input_json['transit_details']['headsign']
            self.vehicle = \
                    input_json['transit_details']['line']['vehicle']['type']
            self.line_name = \
                    input_json['transit_details']['line']['short_name']

    def parsetime(self, time_str):
        hour, mins = time_str.strip('apm').split(':', 1)
        hour = int(hour)
        mins = int(mins)
        if time_str.lower().endswith('pm'):
            hour = (hour + 12) % 24
        return datetime.combine(datetime.now(),
                                dttime(hour, mins))
    def __repr__(self):
        ret = self.travel_mode
        if self.travel_mode == self.MODE_TRANSIT:
            ret += ': ' + self.vehicle + ' ' + self.line_name + \
                    ' [^' + self.headsign + ']: ' + self.departure_stop + \
                    ' ' + str(self.departure_time) + ' -> '  + \
                    self.arrival_stop + ' ' + str(self.arrival_time)
            
        return ret.encode('utf8')

class DirectionsFinder(object):
    def get_directions(self, from_stop, to_stop, time):
        raise NotImplementedError()


class GooglePIDDirectionsFinder(DirectionsFinder):
    def __init__(self, *args, **kwargs):
        super(GooglePIDDirectionsFinder, self).__init__(*args, **kwargs)
        self.directions_url = 'http://maps.googleapis.com/maps/api/directions/json'

    def get_directions(self, from_stop, to_stop, departure_time):

        departure = datetime.combine(
            datetime.now(),
            datetime.strptime(departure_time, "%H:%M").time()
        )

        departure_time = int(time.mktime(departure.timetuple()))

        data = {
            'origin': '%s, Praha' % from_stop.encode('utf8'),
            'destination': 'zastávka %s, Praha' % to_stop.encode('utf8'),
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


