#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import urllib
from datetime import datetime
import time
import json

from alex.applications.PublicTransportInfoEN.site_preprocessing import expand_stop

from alex.tools.apirequest import APIRequest
from alex.utils.cache import lru_cache


class Travel(object):
    """Holder for starting and ending point (and other parameters) of travel."""

    def __init__(self, **kwargs):
        """Initializing (just filling in data).

        Accepted keys: from_city, from_stop, to_city, to_stop, vehicle, max_transfers."""
        self.from_stop_geo = kwargs['from_stop_geo']
        self.to_stop_geo = kwargs['to_stop_geo']
        self.from_city = kwargs['from_city']
        self.from_stop = kwargs['from_stop'] if kwargs['from_stop'] not in ['__ANY__', 'none'] else None
        self.to_city = kwargs['to_city']
        self.to_stop = kwargs['to_stop'] if kwargs['to_stop'] not in ['__ANY__', 'none'] else None
        self.vehicle = kwargs['vehicle'] if kwargs['vehicle'] not in ['__ANY__', 'none', 'dontcare'] else None
        self.max_transfers = (kwargs['max_transfers'] if kwargs['max_transfers'] not in  ['__ANY__', 'none', 'dontcare'] else None)

    def get_minimal_info(self):
        """Return minimal waypoints information
        in the form of a stringified inform() dialogue act."""
        res = []
        if self.from_city != self.to_city or (bool(self.from_stop) != bool(self.to_stop)):
            res.append("inform(from_city='%s')" % self.from_city)
        if self.from_stop is not None:
            res.append("inform(from_stop='%s')" % self.from_stop)
        if self.from_city != self.to_city or (bool(self.from_stop) != bool(self.to_stop)):
            res.append("inform(to_city='%s')" % self.to_city)
        if self.to_stop is not None:
            res.append("inform(to_stop='%s')" % self.to_stop)
        if self.vehicle is not None:
            res.append("inform(vehicle='%s')" % self.vehicle)
        if self.max_transfers is not None:
            res.append("inform(num_transfers='%s')" % str(self.max_transfers))
        return '&'.join(res)


class Directions(Travel):
    """Ancestor class for transit directions, consisting of several routes."""

    def __init__(self, **kwargs):
        if 'travel' in kwargs:
            super(Directions, self).__init__(**kwargs['travel'].__dict__)
        else:
            super(Directions, self).__init__(**kwargs)
        self.routes = []

    def __getitem__(self, index):
        return self.routes[index]

    def __len__(self):
        return len(self.routes)

    def __repr__(self):
        ret = ''
        for i, route in enumerate(self.routes, start=1):
            ret += "ROUTE " + unicode(i) + "\n" + route.__repr__() + "\n\n"
        return ret


class Route(object):
    """Ancestor class for one transit direction route."""

    def __init__(self):
        self.legs = []

    def __repr__(self):
        ret = ''
        for i, leg in enumerate(self.legs, start=1):
            ret += "LEG " + unicode(i) + "\n" + leg.__repr__() + "\n"
        return ret


class RouteLeg(object):
    """One traffic directions leg."""

    def __init__(self):
        self.steps = []

    def __repr__(self):
        return "\n".join(step.__repr__() for step in self.steps)


class RouteStep(object):
    """One transit directions step -- walking or using public transport.
    Data members:
    travel_mode -- TRANSIT / WALKING

    * For TRANSIT steps:
        departure_stop
        departure_time
        arrival_stop
        arrival_time
        headsign       -- direction of the transit line
        vehicle        -- type of the transit vehicle (tram, subway, bus)
        line_name      -- name or number of the transit line

    * For WALKING steps:
        duration       -- estimated walking duration (seconds)
    """

    MODE_TRANSIT = 'TRANSIT'
    MODE_WALKING = 'WALKING'

    def __init__(self, travel_mode):
        self.travel_mode = travel_mode

        if self.travel_mode == self.MODE_TRANSIT:
            self.departure_stop = None
            self.departure_time = None
            self.arrival_stop = None
            self.arrival_time = None
            self.headsign = None
            self.vehicle = None
            self.line_name = None

        elif self.travel_mode == self.MODE_WALKING:
            self.duration = None

    def __repr__(self):
        ret = self.travel_mode
        if self.travel_mode == self.MODE_TRANSIT:
            ret += ': ' + self.vehicle + ' ' + self.line_name + \
                   ' [^' + self.headsign + ']: ' + self.departure_stop + \
                   ' ' + str(self.departure_time) + ' -> ' + \
                   self.arrival_stop + ' ' + str(self.arrival_time)
        elif self.travel_mode == self.MODE_WALKING:
            ret += ': ' + str(self.duration / 60) + ' min, ' + \
                   ((str(self.distance) + ' m') if hasattr(self, 'distance') else '')
        return ret


class DirectionsFinder(object):
    """Abstract ancestor for transit direction finders."""

    def get_directions(self, from_city, from_stop, to_city, to_stop,
                       departure_time=None, arrival_time=None, parameters=None):
        """
        Retrieve the transit directions from the given stop to the given stop
        at the given time.

        Should be implemented in derived classes.
        """
        raise NotImplementedError()


class GoogleDirections(Directions):
    """Traffic directions obtained from Google Maps API."""

    def __init__(self, input_json={}, **kwargs):
        super(GoogleDirections, self).__init__(**kwargs)
        for route in input_json['routes']:
            g_route = GoogleRoute(route)

            # if VEHICLE is defined, than route must be composed of walking and VEHICLE transport
            if kwargs['travel'].vehicle is not None and kwargs['travel'].vehicle not in ['__ANY__', 'none', 'dontcare']:
                route_vehicles = set([step.vehicle for leg in g_route.legs for step in leg.steps if hasattr(step, "vehicle")])
                if len(route_vehicles) != 0 and (len(route_vehicles) > 1 or kwargs['travel'].vehicle not in route_vehicles):
                    continue
            # if MAX_TRANSFERS is defined, than the route must be composed of walking and limited number of transport steps
            if kwargs['travel'].max_transfers is not None and kwargs['travel'].max_transfers not in ['__ANY__', 'none', 'dontcare']:
                num_transfers = len([step for leg in g_route.legs for step in leg.steps if step.travel_mode == GoogleRouteLegStep.MODE_TRANSIT])
                if num_transfers > int(kwargs['travel'].max_transfers) + 1:
                    continue

            self.routes.append(g_route)


class GoogleRoute(Route):

    def __init__(self, input_json):
        super(GoogleRoute, self).__init__()
        for leg in input_json['legs']:
            self.legs.append(GoogleRouteLeg(leg))


class GoogleRouteLeg(RouteLeg):

    def __init__(self, input_json):
        super(GoogleRouteLeg, self).__init__()
        for step in input_json['steps']:
            self.steps.append(GoogleRouteLegStep(step))
        self.distance = input_json['distance']['value']


class GoogleRouteLegStep(RouteStep):

    VEHICLE_TYPE_MAPPING = {
        'RAIL': 'train',
        'METRO_RAIL': 'tram',
        'SUBWAY': 'subway',
        'TRAM': 'tram',
        'MONORAIL': 'monorail',
        'HEAVY_RAIL': 'train',
        'COMMUTER_TRAIN': 'train',
        'HIGH_SPEED_TRAIN': 'train',
        'BUS': 'bus',
        'INTERCITY_BUS': 'bus',
        'TROLLEYBUS': 'bus',
        'SHARE_TAXI': 'bus',
        'FERRY': 'ferry',
        'CABLE_CAR': 'cable_car',
        'GONDOLA_LIFT': 'ferry',
        'FUNICULAR': 'cable_car',
        'OTHER': 'dontcare',
        'Train': 'train',
        'Long distance train': 'train'
    }

    def __init__(self, input_json):
        self.travel_mode = input_json['travel_mode']

        if self.travel_mode == self.MODE_TRANSIT:

            data = input_json['transit_details']
            self.departure_stop = data['departure_stop']['name']
            self.departure_time = datetime.fromtimestamp(data['departure_time']['value'])
            self.arrival_stop = data['arrival_stop']['name']
            self.arrival_time = datetime.fromtimestamp(data['arrival_time']['value'])
            self.headsign = data['headsign']
            # sometimes short_name not present
            if not 'short_name' in data['line']:
                self.line_name = data['line']['name']
            else:
                self.line_name = data['line']['short_name']
            vehicle_type = data['line']['vehicle'].get('type', data['line']['vehicle']['name'])
            self.vehicle = self.VEHICLE_TYPE_MAPPING.get(vehicle_type, vehicle_type.lower())
            # normalize stop names
            self.departure_stop = expand_stop(self.departure_stop)
            self.arrival_stop = expand_stop(self.arrival_stop)
            self.num_stops = data['num_stops']

        elif self.travel_mode == self.MODE_WALKING:
            self.duration = input_json['duration']['value']
            self.distance = input_json['distance']['value']


class GoogleDirectionsFinder(DirectionsFinder, APIRequest):
    """Transit direction finder using the Google Maps query engine."""

    def __init__(self, cfg):
        DirectionsFinder.__init__(self)
        APIRequest.__init__(self, cfg, 'google-directions', 'Google directions query')
        self.directions_url = 'https://maps.googleapis.com/maps/api/directions/json'
        if 'key' in cfg['DM']['directions'].keys():
            self.api_key = cfg['DM']['directions']['key']
        else:
            self.api_key = None

    @lru_cache(maxsize=10)
    def get_directions(self, waypoints, departure_time=None, arrival_time=None):
        """Get Google maps transit directions between the given stops
        at the given time and date.

        The time/date should be given as a datetime.datetime object.
        Setting the correct date is compulsory!
        """

        # TODO: refactor - eliminate from_stop,street,city,borough and make from_place, from_area and use it as:
        # TODO: from_place = from_stop || from_street1 || from_street1&from_street2
        # TODO: from_area = from_borough || from_city
        parameters = list()
        if not waypoints.from_stop_geo:
            from_waypoints =[expand_stop(waypoints.from_stop, False), expand_stop(waypoints.from_city, False)]
            parameters.extend([wp for wp in from_waypoints if wp and wp != 'none'])
        else:
            parameters.append(waypoints.from_stop_geo['lat'])
            parameters.append(waypoints.from_stop_geo['lon'])

        origin = ','.join(parameters).encode('utf-8')

        parameters = list()
        if not waypoints.to_stop_geo:
            to_waypoints = [expand_stop(waypoints.to_stop, False), expand_stop(waypoints.to_city, False)]
            parameters.extend([wp for wp in to_waypoints if wp and wp != 'none'])
        else:
            parameters.append(waypoints.to_stop_geo['lat'])
            parameters.append(waypoints.to_stop_geo['lon'])

        destination = ','.join(parameters).encode('utf-8')

        data = {
            'origin': origin,
            'destination': destination,
            'region': 'us',
            'alternatives': 'true',
            'mode': 'transit',
            'language': 'en',
        }
        if departure_time:
            data['departure_time'] = int(time.mktime(departure_time.timetuple()))
        elif arrival_time:
            data['arrival_time'] = int(time.mktime(arrival_time.timetuple()))

        # add "premium" parameters
        if self.api_key:
            data['key'] = self.api_key
            if waypoints.vehicle:
                data['transit_mode'] = self.map_vehicle(waypoints.vehicle)
            data['transit_routing_preference'] = 'fewer_transfers' if waypoints.max_transfers else 'less_walking'

        self.system_logger.info("Google Directions request:\n" + str(data))

        page = urllib.urlopen(self.directions_url + '?' + urllib.urlencode(data))
        response = json.load(page)
        self._log_response_json(response)

        directions = GoogleDirections(input_json=response, travel=waypoints)
        self.system_logger.info("Google Directions response:\n" +
                                unicode(directions))
        return directions

    def map_vehicle(self, vehicle):
        """maps PTIEN vehicle type to GOOGLE DIRECTIONS query vehicle"""
        # any of standard google inputs
        if vehicle in ['bus', 'subway', 'train', 'tram', 'rail']:
            return vehicle
        # anything on the rail
        if vehicle in ['monorail', 'night_tram', 'monorail']:
            return 'rail'
        # anything on the wheels
        if vehicle in ['trolleybus', 'intercity_bus', 'night_bus']:
            return 'bus'
        # dontcare
        return 'bus|rail'


def _todict(obj, classkey=None):
    """Convert an object graph to dictionary.
    Adapted from:
    http://stackoverflow.com/questions/1036409/recursively-convert-python-object-graph-to-dictionary .
    """
    if isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = _todict(obj[k], classkey)
        return obj
    elif hasattr(obj, "__keylist__"):
        data = {key: _todict(obj[key], classkey)
                for key in obj.__keylist__
                if not callable(obj[key])}
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    elif hasattr(obj, "__dict__"):
        data = {key: _todict(value, classkey)
                for key, value in obj.__dict__.iteritems()
                if not callable(value)}
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    elif hasattr(obj, "__iter__"):
        return [_todict(v, classkey) for v in obj]
    else:
        return obj
