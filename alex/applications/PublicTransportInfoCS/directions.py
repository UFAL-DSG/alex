#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import urllib
from datetime import datetime
from datetime import time as dttime
import time
import json
import os.path
import codecs
from alex.tools.apirequest import APIRequest
from alex.utils.cache import lru_cache


class Directions(object):
    pass


class Route(object):
    pass


class GoogleDirections(Directions):
    def __init__(self, from_stop, to_stop, input_json):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.routes = []
        for route in input_json['routes']:
            self.routes.append(GoogleRoute(route))

    def __len__(self):
        return len(self.routes)

    def __repr__(self):
        ret = ''
        for i, route in enumerate(self.routes, start=1):
            ret += "ROUTE " + unicode(i) + "\n" + route.__repr__() + "\n\n"
        return ret


class GoogleRoute(Route):
    def __init__(self, input_json):
        self.legs = []
        for leg in input_json['legs']:
            self.legs.append(GoogleRouteLeg(leg))

    def __repr__(self):
        ret = ''
        for i, leg in enumerate(self.legs, start=1):
            ret += "LEG " + unicode(i) + "\n" + leg.__repr__() + "\n"
        return ret


class GoogleRouteLeg(object):
    def __init__(self, input_json):
        self.steps = []
        for step in input_json['steps']:
            self.steps.append(GoogleRouteLegStep(step))

    def __repr__(self):
        return "\n".join(step.__repr__() for step in self.steps)


class GoogleRouteLegStep(object):
    """
    One step in a Google route leg -- taking one means of public transport
    or walking.

    Data members:
    travel_mode -- TRANSIT / WALKING

    * For TRANSIT steps:
        departure_stop
        departure_time
        arrival_stop
        arrival_time
        headsign       -- direction of the transit line
        vehicle        -- type of the transit vehicle (TRAM, SUBWAY, BUS)
        line_name      -- name or number of the transit line

    * For WALKING steps:
        duration       -- estimated walking duration (seconds)
    """

    MODE_TRANSIT = "TRANSIT"
    MODE_WALKING = "WALKING"
    STOPS_MAPPING = {'Můstek - A': 'Můstek',
                     'Můstek - B': 'Můstek',
                     'Muzeum - A': 'Muzeum',
                     'Muzeum - C': 'Muzeum',
                     'Florenc - B': 'Florenc',
                     'Florenc - C': 'Florenc'}

    VEHICLE_TYPE_MAPPING = {'HEAVY_RAIL': 'TRAIN',
                            'Train': 'TRAIN',
                            'Long distance train': 'TRAIN'}

    def __init__(self, input_json):
        self.travel_mode = input_json['travel_mode']

        if self.travel_mode == self.MODE_TRANSIT:

            data = input_json['transit_details']
            self.departure_stop = data['departure_stop']['name']
            self.departure_time = datetime.fromtimestamp(data['departure_time']['value'])
            self.arrival_stop = data['arrival_stop']['name']
            self.arrival_time = datetime.fromtimestamp(data['arrival_time']['value'])
            self.headsign = data['headsign']
            self.line_name = data['line']['short_name']
            vehicle_type = data['line']['vehicle'].get('type', data['line']['vehicle']['name'])
            self.vehicle = self.VEHICLE_TYPE_MAPPING.get(vehicle_type, vehicle_type)
            # normalize some stops' names
            self.departure_stop = self.STOPS_MAPPING.get(self.departure_stop, self.departure_stop)
            self.arrival_stop = self.STOPS_MAPPING.get(self.arrival_stop, self.arrival_stop)

        elif self.travel_mode == self.MODE_WALKING:
            self.duration = input_json['duration']['value']
            self.distance = input_json['distance']['value']

    def __repr__(self):
        ret = self.travel_mode
        if self.travel_mode == self.MODE_TRANSIT:
            ret += ': ' + self.vehicle + ' ' + self.line_name + \
                    ' [^' + self.headsign + ']: ' + self.departure_stop + \
                    ' ' + str(self.departure_time) + ' -> ' + \
                    self.arrival_stop + ' ' + str(self.arrival_time)
        elif self.travel_mode == self.MODE_WALKING:
            ret += ': ' + str(self.duration / 60) + ' min, ' + \
                    str(self.distance) + ' m'
        return ret


class DirectionsFinder(object):
    """Abstract ancestor for transit direction finders."""

    def get_directions(self, from_stop, to_stop, time):
        """
        Retrieve the transit directions from the given stop to the given stop
        at the given time.

        Should be implemented in derived classes.
        """
        raise NotImplementedError()


class GooglePIDDirectionsFinder(DirectionsFinder, APIRequest):
    """Transit direction finder using the Google Maps query engine."""

    def __init__(self, cfg):
        DirectionsFinder.__init__(self)
        APIRequest.__init__(self, cfg, 'google-directions', 'Google directions query')
        self.directions_url = 'http://maps.googleapis.com/maps/api/directions/json'

    @lru_cache(maxsize=10)
    def get_directions(self, from_stop, to_stop, from_city, to_city,
                       departure_time=None, arrival_time=None):
        """Get Google maps transit directions between the given stops
        at the given time and date.

        The time/date should be given as a datetime.datetime object.
        Setting the correct date is compulsory!
        """
        data = {
            'origin': ('"zastávka %s", %s, Česká republika' % (from_stop, from_city)).encode('utf-8'),
            'destination': ('"zastávka %s", %s, Česká republika' % (to_stop, to_city)).encode('utf-8'),
            'region': 'cz',
            'sensor': 'false',
            'alternatives': 'true',
            'mode': 'transit',
        }
        if departure_time:
            data['departure_time'] = int(time.mktime(departure_time.timetuple()))
        elif arrival_time:
            data['arrival_time'] = int(time.mktime(arrival_time.timetuple()))

        self.system_logger.info("Google Directions request:\n" + str(data))

        page = urllib.urlopen(self.directions_url + '?' +
                              urllib.urlencode(data))
        response = json.load(page)
        self._log_response_json(response)

        directions = GoogleDirections(from_stop, to_stop, response)
        self.system_logger.info("Google Directions response:\n" +
                                unicode(directions))
        return directions
