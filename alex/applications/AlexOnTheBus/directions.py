#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
import datetime
import time
import json
from collections import namedtuple

import autopath

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
            self.departure_time = \
                self.parsetime(input_json['transit_details']['departure_time']['text'])
            self.arrival_stop = input_json['transit_details']['arrival_stop']['name']
            self.headsign = input_json['transit_details']['headsign']
            self.vehicle = input_json['transit_details']['line']['vehicle']['type']
            self.line_name = input_json['transit_details']['line']['short_name']

    def parsetime(self, time_str):
        dt = datetime.datetime.strptime(time_str, "%H:%M%p")
        return dt


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


