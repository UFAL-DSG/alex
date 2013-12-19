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
from suds.client import Client
from crws_enums import *
import pickle
import gzip
import re
import sys


class Directions(object):
    """Ancestor class for transit directions, consisting of several routes."""

    def __init__(self, from_stop=None, to_stop=None, from_city=None, to_city=None):
        self.from_stop = from_stop
        self.to_stop = to_stop
        self.from_city = from_city
        self.to_city = to_city
        self.routes = []

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
        vehicle        -- type of the transit vehicle (TRAM, SUBWAY, BUS)
        line_name      -- name or number of the transit line

    * For WALKING steps:
        duration       -- estimated walking duration (seconds)
    """

    MODE_TRANSIT = 'TRANSIT'
    MODE_WALKING = 'WALKING'

    # TODO this should be done somehow more clever
    STOPS_MAPPING = {'Můstek - A': 'Můstek',
                     'Můstek - B': 'Můstek',
                     'Muzeum - A': 'Muzeum',
                     'Muzeum - C': 'Muzeum',
                     'Florenc - B': 'Florenc',
                     'Florenc - C': 'Florenc'}

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

    def get_directions(self, from_stop, to_stop, from_city, to_city,
                       departure_time=None, arrival_time=None):
        """
        Retrieve the transit directions from the given stop to the given stop
        at the given time.

        Should be implemented in derived classes.
        """
        raise NotImplementedError()


class GoogleDirections(Directions):
    """Traffic directions obtained from Google Maps API."""

    def __init__(self, from_stop, to_stop, from_city=None, to_city=None, input_json={}):
        super(GoogleDirections, self).__init__(from_stop, to_stop, from_city, to_city)
        for route in input_json['routes']:
            self.routes.append(GoogleRoute(route))


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


class GoogleRouteLegStep(RouteStep):

    def __init__(self, input_json):
        super(GoogleRouteLegStep, self).__init__(input_json['travel_mode'])

        if self.travel_mode == self.MODE_TRANSIT:

            self.departure_stop = input_json['transit_details']['departure_stop']['name']
            self.departure_time = datetime.fromtimestamp(input_json['transit_details']
                                                         ['departure_time']['value'])
            self.arrival_stop = input_json['transit_details']['arrival_stop']['name']
            self.arrival_time = datetime.fromtimestamp(input_json['transit_details']
                                                       ['arrival_time']['value'])
            self.headsign = input_json['transit_details']['headsign']
            self.vehicle = input_json['transit_details']['line']['vehicle']['type']
            self.line_name = input_json['transit_details']['line']['short_name']
            # normalize some stops' names
            self.departure_stop = self.STOPS_MAPPING.get(self.departure_stop, self.departure_stop)
            self.arrival_stop = self.STOPS_MAPPING.get(self.arrival_stop, self.arrival_stop)

        elif self.travel_mode == self.MODE_WALKING:
            self.duration = input_json['duration']['value']
            self.distance = input_json['distance']['value']


class CRWSDirections(Directions):
    """Traffic directions obtained from CR Web Service (CHAPS/IDOS)."""

    def __init__(self, from_stop, to_stop, from_city=None, to_city=None, input_data={}):
        super(CRWSDirections, self).__init__(from_stop, to_stop, from_city, to_city)
        if hasattr(input_data, 'oConnInfo'):
            for route in input_data.oConnInfo.aoConnections:
                self.routes.append(CRWSRoute(route))


class CRWSRoute(Route):

    def __init__(self, input_data):
        super(CRWSRoute, self).__init__()
        # only one leg currently
        self.legs.append(CRWSRouteLeg(input_data))


class CRWSRouteLeg(RouteLeg):

    def __init__(self, input_data):
        super(CRWSRouteLeg, self).__init__()
        for step in input_data.aoTrains:
            # treat walking steps separately
            # (as they are part of transit steps in the underlying representation)
            if hasattr(step, '_iLinkDist'):
                self.steps.append(CRWSRouteStep(CRWSRouteStep.MODE_WALKING, step._iLinkDist))
            # normal transit steps
            self.steps.append(CRWSRouteStep(CRWSRouteStep.MODE_TRANSIT, step))


class CRWSRouteStep(RouteStep):

    VEHICLE_TYPE_MAPPING = {'bus': 'BUS',
                            'autobus': 'BUS',
                            'local line': 'BUS',
                            'long-distance line': 'INTERCITY_BUS',
                            'international line': 'INTERCITY_BUS',
                            'tram': 'TRAM',
                            'tramvaj': 'TRAM',
                            'metro': 'SUBWAY',
                            'local train': 'TRAIN',
                            'fast train': 'TRAIN',
                            'Express': 'TRAIN',
                            'Intercity': 'TRAIN',
                            'Eurocity': 'TRAIN',
                            'EuroNight': 'TRAIN',
                            'SuperCity': 'TRAIN',
                            'LEOExpress': 'TRAIN',
                            'RegionalExpress': 'TRAIN',
                            'Tanie Linie Kolejowe': 'TRAIN',
                            'Regionalzug': 'TRAIN',
                            'Express InterCity': 'TRAIN',
                            'funicular': 'CABLE_CAR',
                            'trolejbus': 'TROLLEYBUS',
                            'trolley bus': 'TROLLEYBUS',
                            'trolleybus': 'TROLLEYBUS',
                            'ship': 'FERRY', }

    def __init__(self, travel_mode, input_data):
        super(CRWSRouteStep, self).__init__(travel_mode)

        if self.travel_mode == self.MODE_TRANSIT:

            data_from_stop = input_data.oTrainData.aoRoute[input_data._iFrom]
            data_to_stop = input_data.oTrainData.aoRoute[input_data._iTo]
            data_final_stop = input_data.oTrainData.aoRoute[-1]

            self.departure_stop = data_from_stop.oStation._sName
            self.departure_time = input_data._dtDateTime1
            self.arrival_stop = data_to_stop.oStation._sName
            self.arrival_time = input_data._dtDateTime2
            self.headsign = data_final_stop.oStation._sName
            self.vehicle = self.VEHICLE_TYPE_MAPPING[input_data.oTrainData.oInfo._sTypeName]
            self.line_name = input_data.oTrainData.oInfo._sNum1
            # add train names to line numbers
            if self.vehicle == 'TRAIN':
                train_name = input_data.oTrainData.oInfo._sNum2
                train_type_shortcut = input_data.oTrainData.oInfo._sType
                if train_name.startswith(train_type_shortcut + ' '):
                    self.line_name += ' ' + train_name
                else:
                    self.line_name = ' '.join((train_type_shortcut, self.line_name, train_name))
            elif self.vehicle in ['BUS', 'INTERCITY_BUS'] and re.match(r'[0-9]{6}', self.line_name):
                self.line_name = self.line_name[0:3] + ' ' + self.line_name[3:6]
            # normalize some stops' names
            self.departure_stop = self.STOPS_MAPPING.get(self.departure_stop, self.departure_stop)
            self.arrival_stop = self.STOPS_MAPPING.get(self.arrival_stop, self.arrival_stop)

        elif self.travel_mode == self.MODE_WALKING:
            # input data in this case are only the amount of minutes needed for walking
            self.duration = 60 * input_data


class GoogleDirectionsFinder(DirectionsFinder, APIRequest):
    """Transit direction finder using the Google Maps query engine."""

    def __init__(self, cfg):
        DirectionsFinder.__init__(self)
        APIRequest.__init__(self, cfg, 'google-directions', 'Google directions query')
        self.directions_url = 'http://maps.googleapis.com/maps/api/directions/json'

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

        directions = GoogleDirections(from_stop, to_stop, from_city, to_city, response)
        self.system_logger.info("Google Directions response:\n" +
                                unicode(directions))
        return directions


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


class CRWSDirectionsFinder(DirectionsFinder, APIRequest):
    """Direction finder using the CR Web Service provided by CHAPS (a.k.a. IDOS)."""

    # file name for caching 'Combination Info'
    COMBINATION_INFO_FNAME = 'crws_combination.pickle.gz'

    def __init__(self, cfg):
        DirectionsFinder.__init__(self)
        APIRequest.__init__(self, cfg, 'crws-directions', 'CRWS directions query')
        # create the client
        self.client = Client("http://crws.timetable.cz/CR.svc?wsdl")
        # obtain user information
        self.user_id = cfg['CRWS']['user_id']
        self.user_desc = cfg['CRWS']['user_desc']
        self.max_connections_count = cfg['CRWS']['max_connections_count']
        # renew list of lists
        self.combinations = self._load_combination_info()
        self.default_comb_id = self.combinations[0]['_sID']
        # parse list of lists and get ID of cities list and stop names list
        self.city_list_id, self.stops_list_for_city = self._get_stop_list_ids()

    def search_stop(self, stop_mask, city=None):
        return self.client.service.SearchGlobalListItemInfo(
            self.user_id,
            self.user_desc,
            self.default_comb_id,
            self.stops_list_for_city.get(city, 0), # list ID (0 = all)
            stop_mask, # mask
            SEARCHMODE.EXACT | SEARCHMODE.USE_PRIORITY, # search mode
            0, # max count
            REG.SMART, # return regions
            0, # skip count
            TTLANG.ENGLISH # language
        )

    def search_city(self, city_mask):
        return self.search_stop(city_mask, self.city_list_id)

    def get_directions(self, from_stop=None, to_stop=None, from_city=None, to_city=None,
                       departure_time=None, arrival_time=None):
        # find from and to objects
        from_obj = None
        to_obj = None
        if from_stop is not None:
            from_obj = self.search_stop(from_stop, from_city)
        else:
            from_obj = self.search_city(from_city)
        if to_stop is not None:
            to_obj = self.search_stop(to_stop, to_city)
        else:
            to_obj = self.search_city(to_city)
        # handle times
        is_departure = True
        ts = departure_time or datetime.now()
        if arrival_time is not None:
            is_departure = False
            ts = arrival_time
        self.system_logger.info(("CRWS Request for connection:\n\nFROM: %s\n\nTO: %s\n\n" +
                                "TIME_STAMP: %s\nIS_DEPARTURE: %s\n") %
                                (from_obj, to_obj, ts, is_departure))
        # request the connections from CRWS
        response = self.client.service.SearchConnectionInfo(
            self.user_id,
            self.user_desc,
            self.default_comb_id,
            from_obj,
            to_obj,
            None, # via
            None, # change
            ts, # timestamp of arrival or departure
            is_departure, # is departure? (or arrival)
            None, # connection parameters
            REMMASK.NONE,
            SEARCHMODE.NONE,
            0, # max objects count
            self.max_connections_count, # max connections count
            REG.SMART, # return regions
            TTINFODETAILS.ITEM,
            COOR.DEFAULT,
            "", # no substitutions, textual format
            TTDETAILS.ROUTE_FROMTO | TTDETAILS.ROUTE_CHANGE | TTDETAILS.TRAIN_INFO,
            TTLANG.ENGLISH,
            0)
        # log the response
        self._log_response_json(_todict(response, '_origClassName'))
        # parse the results
        directions = CRWSDirections(from_stop, to_stop, from_city, to_city, response)
        self.system_logger.info("CRWS Directions response:\n" + unicode(directions))

        return directions

    def _get_stop_list_ids(self):
        """Retrieve IDs of lists of stops for all available cities, plus the ID of the list of cities."""
        cities_list = None
        stop_lists = {}
        for comb in self.combinations:
            for list_info in comb['aoGlobalLists']:
                if cities_list is None:
                    if list_info['asName'][0] == 'města a obce':
                        cities_list = list_info['_iID']
                matching = re.match(r'zastávky \(([^)]+)\)', list_info['asName'][0])
                if matching:
                    stop_lists[matching.group(1)] = list_info['_iID']
        return cities_list, stop_lists

    def _load_combination_info(self):
        """Get a list of accessible object lists (cached using pickles)."""
        # try to load cached data, set cached date to -Inf on failure
        try:
            fh = gzip.open(self.COMBINATION_INFO_FNAME, 'r')
            unpickler = pickle.Unpickler(fh)
            comb_info = unpickler.load()
            last_date = unpickler.load()
            fh.close()
        except:
            comb_info = None
            last_date = datetime(1970, 1, 1)
        # update the combination info
        new_comb_info = self.client.service.GetCombinationInfo(
            self.user_id,
            self.user_desc,
            None, # asCombId (None = all)
            last_date, # last date this function was called on
            TTLANG.ENGLISH  # language
        )
        self.response = new_comb_info
        # process the response
        if len(new_comb_info) == 2:  # reply contains new data and timestamp
            last_date = new_comb_info[1]
            new_comb_info = _todict(new_comb_info[0][0], '_origClassName')
        else:  # reply contains (old) timestamp only -- use cached data
            new_comb_info = comb_info
        try:
            fh = gzip.open(self.COMBINATION_INFO_FNAME, 'wb')
            pickle.Pickler(fh, pickle.HIGHEST_PROTOCOL).dump(new_comb_info)
            pickle.Pickler(fh, pickle.HIGHEST_PROTOCOL).dump(last_date)
            fh.close()
        except Exception as e:
            print >> sys.stderr, e
        return new_comb_info
