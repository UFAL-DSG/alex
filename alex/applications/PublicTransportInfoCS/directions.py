#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
from datetime import datetime
from datetime import time as dttime
import time
import json
import os.path

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
        elif self.travel_mode == self.MODE_WALKING:
            self.duration = input_json['duration']['value']
            self.distance = input_json['distance']['value']

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
                    ' ' + str(self.departure_time) + ' -> ' + \
                    self.arrival_stop + ' ' + str(self.arrival_time)
        elif self.travel_mode == self.MODE_WALKING:
            ret += ': ' + str(self.duration / 60) + ' min, ' + \
                    str(self.distance) + ' m'
        return ret.encode('utf8')


class DirectionsFinder(object):
    """Abstract ancestor for transit direction finders."""

    def get_directions(self, from_stop, to_stop, time):
        """
        Retrieve the transit directions from the given stop to the given stop
        at the given time.

        Should be implemented in derived classes.
        """
        raise NotImplementedError()


class GooglePIDDirectionsFinder(DirectionsFinder):
    """Transit direction finder using the Google Maps query engine."""

    def __init__(self, cfg):
        super(GooglePIDDirectionsFinder, self).__init__()
        self.system_logger = cfg['Logging']['system_logger']
        self.session_logger = cfg['Logging']['session_logger']
        self.directions_url = \
                'http://maps.googleapis.com/maps/api/directions/json'

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
        self.system_logger.info("Google Directions request:\n" + str(data))

        page = urllib.urlopen(self.directions_url + '?' +
                              urllib.urlencode(data))
        response = json.load(page)
        self._log_response_json(response)

        directions = GoogleDirections(response)
        self.system_logger.info("Google Directions response:\n" +
                                str(directions).decode('utf8'))
        return directions

    def _log_response_json(self, data):
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f')
        fname = os.path.join(self.system_logger.get_session_dir_name(),
                             'google-directions-{t}.json'.format(t=timestamp))
        fh = open(fname, 'w')
        json.dump(data, fh)
        fh.close()
