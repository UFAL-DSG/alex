#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import urllib
from datetime import datetime, timedelta
import os.path
import time
import json
import pprint
from suds.client import Client
from alex.applications.PublicTransportInfoCS.platform_info import \
    CRWSPlatformInfo
from crws_enums import *
import pickle
import gzip
import re
import sys
import codecs
from alex.tools.apirequest import APIRequest
from alex.utils.cache import lru_cache
from alex.utils.config import online_update, to_project_path
from alex.applications.PublicTransportInfoCS.data.convert_idos_stops import expand_abbrevs


class Travel(object):
    """Holder for starting and ending point (and other parameters) of travel."""

    def __init__(self, **kwargs):
        """Initializing (just filling in data).

        Accepted keys: from_city, from_stop, to_city, to_stop, vehicle, max_transfers."""
        self.from_city = kwargs['from_city']
        self.from_stop = kwargs['from_stop'] if kwargs['from_stop'] not in ['__ANY__', 'none'] else None
        self.to_city = kwargs['to_city']
        self.to_stop = kwargs['to_stop'] if kwargs['to_stop'] not in ['__ANY__', 'none'] else None
        self.vehicle = kwargs['vehicle'] if kwargs['vehicle'] not in ['__ANY__', 'none', 'dontcare'] else None
        self.max_transfers = (kwargs['max_transfers']
                              if kwargs['max_transfers'] not in  ['__ANY__', 'none', 'dontcare']
                              else None)

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


class DirectionsFinderException(Exception):
    pass


class NotSupported(DirectionsFinderException):
    pass


class DirectionsFinder(object):
    """Abstract ancestor for transit direction finders."""

    def get_directions(self, travel, departure_time=None, arrival_time=None):
        """Retrieve the directions for the given travel route at the given time."""
        raise NotImplementedError()

    def get_platform(self, platform_info):
        """Retrieve the platform information for the given platform parameters."""
        raise NotSupported()


class GoogleDirections(Directions):
    """Traffic directions obtained from Google Maps API."""

    def __init__(self, input_json={}, **kwargs):
        super(GoogleDirections, self).__init__(**kwargs)
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

    VEHICLE_TYPE_MAPPING = {'HEAVY_RAIL': 'train',
                            'Train': 'train',
                            'Long distance train': 'train'}

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
            self.vehicle = self.VEHICLE_TYPE_MAPPING.get(vehicle_type, vehicle_type.lower())
            # normalize some stops' names
            self.departure_stop = self.STOPS_MAPPING.get(self.departure_stop, self.departure_stop)
            self.arrival_stop = self.STOPS_MAPPING.get(self.arrival_stop, self.arrival_stop)

        elif self.travel_mode == self.MODE_WALKING:
            self.duration = input_json['duration']['value']
            self.distance = input_json['distance']['value']


class CRWSDirections(Directions):
    """Traffic directions obtained from CR Web Service (CHAPS/IDOS)."""

    def __init__(self, input_data={}, finder=None, **kwargs):
        # basic initialization
        super(CRWSDirections, self).__init__(**kwargs)
        self.finder = None
        self.handle = None
        # appear totally empty in case of any errors
        if hasattr(input_data, '_iResult') and input_data._iResult != 0:
            return
        # remember finder and handle if we got them
        if finder is not None:
            self.handle = input_data._iHandle
            self.finder = finder
        # parse the connection information, if available
        if hasattr(input_data, 'oConnInfo'):
            for route in input_data.oConnInfo.aoConnections:
                self.routes.append(CRWSRoute(route, self.finder))

    def __getitem__(self, index):
        # try to load further data if it is missing
        if index >= len(self) and self.finder and self.handle:
            data = self.finder.get_directions_by_handle(self.handle, index + 1)
            new_routes = []
            if hasattr(data, 'aoConnections'):
                for route in data.aoConnections[len(self):]:
                    new_routes.append(CRWSRoute(route, self.finder))
            self.finder.system_logger.info("CRWS additional directions loaded:\n" +
                                           '\n'.join([unicode(r) for r in new_routes]))
            self.routes.extend(new_routes)
        return super(CRWSDirections, self).__getitem__(index)

    def __repr__(self):
        if not self.routes and self.finder is not None:
            return '(async search in progress)'
        return super(CRWSDirections, self).__repr__()


class CRWSRoute(Route):

    def __init__(self, input_data, finder=None):
        super(CRWSRoute, self).__init__()
        # only one leg currently
        self.legs.append(CRWSRouteLeg(input_data, finder))


class CRWSRouteLeg(RouteLeg):

    def __init__(self, input_data, finder=None):
        super(CRWSRouteLeg, self).__init__()
        for step in input_data.aoTrains:
            # treat walking steps separately
            # (as they are part of transit steps in the underlying representation)
            if hasattr(step, '_iLinkDist'):
                self.steps.append(CRWSRouteStep(CRWSRouteStep.MODE_WALKING, step._iLinkDist))
            # normal transit steps
            self.steps.append(CRWSRouteStep(CRWSRouteStep.MODE_TRANSIT, step, finder))


class CRWSRouteStep(RouteStep):

    VEHICLE_TYPE_MAPPING = {'bus': 'bus',
                            'autobus': 'bus',
                            'local line': 'bus',
                            'night line bus': 'night_bus',
                            'regional line bus': 'intercity_bus',
                            'long-distance line': 'intercity_bus',
                            'international line': 'intercity_bus',
                            'tram': 'tram',
                            'tramvaj': 'tram',
                            'night line tram': 'night_tram',
                            'metro': 'subway',
                            'local train': 'local_train',
                            'fast train': 'fast_train',
                            'higher quality fast train': 'fast_train',
                            'Express': 'express_train',
                            'Intercity': 'intercity_train',
                            'Eurocity': 'eurocity_train',
                            'EuroNight': 'euronight_train',
                            'SuperCity': 'supercity_train',
                            'LEOExpress': 'train',
                            'railjet': 'train',
                            'RegionalExpress': 'regional_fast_train',
                            'semi fast train': 'regional_fast_train',
                            'Tanie Linie Kolejowe': 'train',
                            'Regionalzug': 'local_train',
                            'Express InterCity': 'intercity_train',
                            'funicular': 'cable_car',
                            'trolejbus': 'trolleybus',
                            'trolley bus': 'trolleybus',
                            'trolleybus': 'trolleybus',
                            'ship': 'ferry',
                            'substitute traffic': 'substitute_traffic',
                            'substitute traffic - Bus': 'substitute_bus'}

    def __init__(self, travel_mode, input_data, finder=None):
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
            # ignore bus line numbers if they are too long
            if self.vehicle in ['bus', 'intercity_bus'] and len(self.line_name) > 4:
                self.line_name = ''
            # replace train numbers with names (e.g. 'Hutník', 'Pendolino' etc.) or nothing
            if self.vehicle.endswith('train'):
                self.line_name = (input_data.oTrainData.oInfo._sNum2
                                  if hasattr(input_data.oTrainData.oInfo, '_sNum2') and input_data.oTrainData.oInfo
                                  else '')
                if self.line_name:  # strip train type shortcut if it's contained in the name
                    train_type_shortcut = input_data.oTrainData.oInfo._sType
                    if self.line_name.startswith(train_type_shortcut + ' '):
                        self.line_name = self.line_name[len(train_type_shortcut) + 1:]
            # if finder is present, use its mapping to convert stop names into pronounceable form
            if finder is not None:
                self.departure_stop = finder.get_stop_full_name(self.departure_stop)
                self.arrival_stop = finder.get_stop_full_name(self.arrival_stop)
                self.headsign = finder.get_stop_full_name(self.headsign)
            # further normalize some stops' names
            self.departure_stop = self.STOPS_MAPPING.get(self.departure_stop, self.departure_stop)
            self.arrival_stop = self.STOPS_MAPPING.get(self.arrival_stop, self.arrival_stop)

            self.departure_stop = self.departure_stop.replace(',,', ', ')
            self.arrival_stop = self.arrival_stop.replace(',,', ', ')
            self.headsign = self.headsign.replace(',,', ', ')

        elif self.travel_mode == self.MODE_WALKING:
            # input data in this case are only the amount of minutes needed for walking
            self.duration = 60 * input_data


class GoogleDirectionsFinder(DirectionsFinder, APIRequest):
    """Transit direction finder using the Google Maps query engine."""

    def __init__(self, cfg):
        DirectionsFinder.__init__(self)
        APIRequest.__init__(self, cfg, 'google-directions', 'Google directions query')
        self.directions_url = 'http://maps.googleapis.com/maps/api/directions/json'

    @lru_cache(maxsize=10)
    def get_directions(self, waypoints, departure_time=None, arrival_time=None):
        """Get Google maps transit directions between the given stops
        at the given time and date.

        The time/date should be given as a datetime.datetime object.
        Setting the correct date is compulsory!
        """
        data = {
            'origin': ('"zastávka %s", %s, Česká republika' %
                       (waypoints.from_stop, waypoints.from_city)).encode('utf-8'),
            'destination': ('"zastávka %s", %s, Česká republika' %
                            (waypoints.to_stop, waypoints.to_city)).encode('utf-8'),
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

        directions = GoogleDirections(input_json=response, travel=waypoints)
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
    # name of the file containing city + stop -> IDOS-list + IDOS-stop mapping
    CONVERSION_FNAME = 'data/idos_map.tsv'

    def __init__(self, cfg):
        DirectionsFinder.__init__(self)
        APIRequest.__init__(self, cfg, 'crws-directions', 'CRWS directions query')
        # create the client
        self.client = Client("http://crws.timetable.cz/CR.svc?wsdl")
        # obtain user information
        self.user_id = cfg['CRWS']['user_id']
        self.user_desc = cfg['CRWS']['user_desc']
        self.max_connections_count = cfg['CRWS']['max_connections_count']
        self.file_dir = os.path.dirname(os.path.abspath(__file__))
        # renew list of lists
        self.combinations = self._load_combination_info()
        self.default_comb_id = self.combinations[0]['_sID']
        # parse list of lists and get ID of cities list and stop names list
        self.city_list_id, self.train_list_id, self.stops_list_for_city = \
            self._get_stop_list_ids()
        # load mapping from ALEX stops to IDOS stops and back
        self.mapping, self.reverse_mapping = self._load_stops_mapping()

    def search_stop(self, stop_mask, city=None, max_count=0, skip_count=0):
        """Search the given stop database in IDOS for the given city."""
        return self.client.service.SearchGlobalListItemInfo(
            self.user_id,
            self.user_desc,
            self.default_comb_id,
            self.stops_list_for_city.get(city, 0), # list ID (0 = all)
            stop_mask, # mask
            SEARCHMODE.EXACT | SEARCHMODE.USE_PRIORITY, # search mode
            max_count, # max count
            REG.SMART, # return regions
            skip_count, # skip count
            TTLANG.ENGLISH # language
        )

    def search_train_station(self, stop_mask, max_count=0, skip_count=0):
        """Seach train station database in IDOS."""
        return self.client.service.SearchGlobalListItemInfo(
            self.user_id,
            self.user_desc,
            self.default_comb_id,
            self.train_list_id,
            stop_mask, # mask
            SEARCHMODE.EXACT | SEARCHMODE.USE_PRIORITY, # search mode
            max_count, # max count
            REG.SMART, # return regions
            skip_count, # skip count
            TTINFODETAILS.STATIONSEXT,
            COOR.DEFAULT,
            TTLANG.ENGLISH # language
        )

    def search_city(self, city_mask):
        return self.search_stop(city_mask, self.city_list_id)



    @lru_cache(maxsize=10)
    def get_platform(self, platform_info):
        # try to map from-to to IDOS identifiers, default to originals
        self.system_logger.info("ALEX: Looking up platform for: %s -- %s" %
                                (platform_info.from_stop,
                                 platform_info.to_stop))

        if platform_info.from_city != 'none' and platform_info.from_stop != 'none':
                from_obj = self.search_train_station("%s, %s" % (
                                             platform_info.from_city,
                                             platform_info.from_stop))
        elif platform_info.from_city != 'none':
            from_obj = self.search_train_station("%s" % (
                                             platform_info.from_city, ))
        elif platform_info.from_stop != 'none':
            from_obj = self.search_train_station("%s" % (
                                             platform_info.from_stop, ))
        else:
            raise Exception()

        train_name = None
        if platform_info.to_city != 'none' and platform_info.to_stop != \
                'none':
                to_obj = self.search_train_station("%s, %s" % (
                                             platform_info.to_city,
                                             platform_info.to_stop))
        elif platform_info.to_city != 'none':
            to_obj = self.search_train_station("%s" % (
                                             platform_info.to_city, ))
        elif platform_info.to_stop != 'none':
            to_obj = self.search_train_station("%s" % (
                                             platform_info.to_stop, ))
        elif platform_info.train_name != 'none':
            to_obj = None
            train_name = platform_info.train_name
        else:
            raise Exception()



        self.system_logger.info("SEARCHING: from(%s, %s)" % (
                                             platform_info.from_city,
                                             platform_info.from_stop))
        self.system_logger.info("SEARCHING: to(%s, %s)" % (
                                             platform_info.to_city,
                                             platform_info.to_stop))

        if from_obj and (to_obj or train_name):
            # Get the entries in the departure table at the from station.
            response = self.client.service.SearchDepartureTableInfo(
                self.user_id,
                self.user_desc,
                self.default_comb_id,
                from_obj[0],
                True,
                datetime.min, # timestamp of arrival or departure
                True,
                SEARCHMODE.EXACT,
                1,
                REG.SMART,
                TTINFODETAILS.STATIONSEXT,
                None,
                TTDETAILS.STANDS,
                TTLANG.ENGLISH
            )

            self._log_response_json(_todict(response, '_origClassName'))

            # Extract the departure table entry.
            platform_info = CRWSPlatformInfo(response, self)
            if from_obj and to_obj:
                self.system_logger.info("CRWS Looking by destination station.")
                platform_res = platform_info.find_platform_by_station(to_obj)
            elif from_obj and train_name:
                self.system_logger.info("CRWS Looking by train name.")
                platform_res = platform_info.find_platform_by_train_name(platform_info.train_name)
            else:
                raise Exception("Incorrect state!")

            self.system_logger.info("CRWS PlatformFinder response:\n" + unicode(
                platform_res))

            return platform_res
        else:
            self.system_logger.info("PlatformFinder from and to has not "
                                    "been found:\n" + unicode(
                platform_info))
            return None

    @lru_cache(maxsize=10)
    def get_directions(self, travel, departure_time=None, arrival_time=None):
        # try to map from-to to IDOS identifiers, default to originals
        self.system_logger.info("ALEX: %s -- %s, %s -- %s" %
                                (travel.from_stop, travel.from_city,
                                 travel.to_stop, travel.to_city))
        from_city, from_stop = self.mapping.get((travel.from_city, travel.from_stop),
                                                (travel.from_city, travel.from_stop))
        to_city, to_stop = self.mapping.get((travel.to_city, travel.to_stop),
                                            (travel.to_city, travel.to_stop))
        self.system_logger.info("IDOS: %s -- %s,  %s -- %s" % (from_stop, from_city, to_stop, to_city))
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
        # a workaround for a daylight saving bug in SUDS, remove when fixed in SUDS
        # (see https://fedorahosted.org/suds/ticket/353).
        if time.localtime(time.mktime(ts.timetuple())).tm_isdst:
            ts -= timedelta(hours=1)
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
            self._create_search_parameters(travel),  # detailed search parameters
            REMMASK.NONE,
            SEARCHMODE.NONE,
            0, # max objects count
            self.max_connections_count, # max connections count (-1 = only return handle)
            REG.SMART, # return regions
            TTINFODETAILS.ITEM,
            COOR.DEFAULT,
            "", # no substitutions, textual format
            TTDETAILS.ROUTE_FROMTO | TTDETAILS.ROUTE_CHANGE | TTDETAILS.TRAIN_INFO,
            TTLANG.ENGLISH,
            0)
        # (use this to log raw XML requests/responses)
        # # xml_data = unicode(self.client.last_sent())
        # # xml_data += "\n" + unicode(self.client.last_received())
        # # self.session_logger.external_data_file(ftype, fname, xml_data.encode('UTF-8'))
        # log the response
        self._log_response_json(_todict(response, '_origClassName'))
        # parse the results
        directions = CRWSDirections(input_data=response, finder=self, travel=travel)
        self.system_logger.info("CRWS Directions response:\n" + unicode(directions))

        return directions

    def get_directions_by_handle(self, handle, limit):
        """Retrieve additional routes for the given connection handle."""
        self.system_logger.info(("CRWS Request for additional routes:\n\nHANDLE: %s, LIMIT: %d") %
                                (str(handle), limit))
        # request the connections from CRWS
        response = self.client.service.GetConnectionsPage(
            self.user_id,
            self.user_desc,
            self.default_comb_id,
            handle,
            0, # reference connection
            False, # return connections before the reference ?
            0, # currently listed connections (it will return the earlier connections anyway, so we just ignore this)
            limit, # maximum connection count
            REMMASK.NONE,
            COOR.DEFAULT,
            "", # no substitutions, textual format
            TTDETAILS.ROUTE_FROMTO | TTDETAILS.ROUTE_CHANGE | TTDETAILS.TRAIN_INFO,
            TTLANG.ENGLISH)
        self._log_response_json(_todict(response, '_origClassName'))
        return response

    def _get_stop_list_ids(self):
        """Retrieve IDs of lists of stops for all available cities, plus the ID of the list of cities."""
        cities_list = None
        train_list = None
        stop_lists = {}
        for comb in self.combinations:
            for list_info in comb['aoGlobalLists']:
                if cities_list is None:
                    if list_info['asName'][0] == 'města a obce':
                        cities_list = list_info['_iID']
                if train_list is None:
                    if list_info['asName'][0] == 'stanice (vlak)':
                        train_list = list_info['_iID']
                matching = re.match(r'^(?:zastávky|stanice) \(([^)]+)\)$', list_info['asName'][0])
                if matching:
                    stop_lists[matching.group(1)] = list_info['_iID']
        return cities_list, train_list, stop_lists

    def _load_combination_info(self):
        """Get a list of accessible object lists (cached using pickles)."""
        # try to load cached data, set cached date to -Inf on failure
        try:
            fh = gzip.open(os.path.join(self.file_dir, self.COMBINATION_INFO_FNAME), 'r')
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
            try:
                fh = gzip.open(os.path.join(self.file_dir, self.COMBINATION_INFO_FNAME), 'wb')
                pickle.Pickler(fh, pickle.HIGHEST_PROTOCOL).dump(new_comb_info)
                pickle.Pickler(fh, pickle.HIGHEST_PROTOCOL).dump(last_date)
                fh.close()
            except Exception as e:
                print >> sys.stderr, e
        else:  # reply contains (old) timestamp only -- use cached data
            new_comb_info = comb_info
        return new_comb_info

    def _load_stops_mapping(self):
        """Load the mapping from ALEX stops format (city + pronounceable name) into IDOS
        format (IDOS list + IDOS name including abbreviations and whatever rubbish).
        Also creates a reverse mapping of stop names, so that pronounceable names are
        returned.

        Updates the mapping from the server if needed

        @rtype: tuple
        @return: Mapping (city, stop) -> (idos_list, idos_stop), mapping (idos_stop) -> (stop)
        """
        # update the mapping file from the server
        online_update(to_project_path(os.path.join(os.path.dirname(__file__), self.CONVERSION_FNAME)))
        # load the mapping
        mapping = {}
        reverse_mapping = {}
        with codecs.open(os.path.join(self.file_dir, self.CONVERSION_FNAME), 'r', 'UTF-8') as fh:
            for line in fh:
                line = line.strip()
                city, stop, idos_list, idos_stop = line.split("\t")
                mapping[(city, stop)] = (idos_list, idos_stop)
                idos_stop = self._normalize_idos_name(idos_stop)
                reverse_mapping[idos_stop] = stop
        return mapping, reverse_mapping

    def _create_search_parameters(self, parameters):
        params = self.client.factory.create('ConnectionParmsInfo')
        # allow some walking at start and end of route
        params._iMaxArcLengthFrom = 4
        params._iMaxArcLengthTo = 4
        params._iNodeFrom = 1
        params._iNodeTo = 1
        # TODO number of transfers (_iMaxChange)
        if parameters is not None:
            # vehicle type limitations (IDs taken from CRWS)
            if parameters.vehicle == 'train':
                params._aiTrTypeID = '100 150 151 152 153'
            elif parameters.vehicle == 'bus':
                params._aiTrTypeID = '154 301 200 201 202 304 308'
            elif parameters.vehicle == 'tram':
                params._aiTrTypeID = '300 309'
            elif parameters.vehicle == 'subway':
                params._aiTrTypeID = '302'
            elif parameters.vehicle == 'trolleybus':
                params._aiTrTypeID = '306'
            elif parameters.vehicle == 'ferry':
                params._aiTrTypeID = '155 307 507'
            elif parameters.vehicle == 'cable_car':
                params._aiTrTypeID = '303'
            # number of transfers limitations
            if parameters.max_transfers != 'none':
                params._iMaxChange = parameters.max_transfers
        return params

    def _normalize_idos_name(self, idos_stop):
        """Normalize a name of an IDOS stop by stripping punctuation and lowercasing, in order
        to get a reverse mapping to a full name even if punctuation or casing differs."""
        idos_stop = re.sub(r'[\.,\-–\(\)\{\}\[\];](?: [\.,\-–\(\)\{\}\[\];])*', r' ', ' ' + idos_stop + ' ').lower()
        idos_stop = re.sub(r' +', r' ', idos_stop)
        return idos_stop

    def get_stop_full_name(self, idos_stop):
        """Try to obtain a full name from the reverse mapping of IDOS -> Alex; run the abbreviation
        expansion regexps if not found."""
        if idos_stop is None:
            return None
        stop_full_name = self.reverse_mapping.get(self._normalize_idos_name(idos_stop))
        if stop_full_name is None:  # not found in the mapping --> expand abbreviations
            stop_full_name, _ = expand_abbrevs(idos_stop)
            self.reverse_mapping[self._normalize_idos_name(idos_stop)] = stop_full_name
        return stop_full_name
