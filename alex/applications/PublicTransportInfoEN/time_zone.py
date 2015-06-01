#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import urllib
from datetime import datetime
import json

# from alex.utils.cache import lru_cache
from alex.tools.apirequest import APIRequest


class Time(object):
    pass

# class GoogleTime(Time):
#
#     def __init__(self, input_json):
#         # get current time
#         self.time = input_json['response']
#
#     def __repr__(self):
#         ret = self.condition + ', '
#         if hasattr(self, 'min_temp'):
#             ret += str(self.min_temp) + ' – ' + str(self.max_temp)
#         else:
#             ret += str(self.temp)
#         return ret + ' °C'



class GoogleTimeFinder(APIRequest):

    def __init__(self, cfg):
        APIRequest.__init__(self, cfg, 'openweathermap', 'OpenWeatherMap query')


    def obtain_geo_codes(self, place='New York'):
        """:
        :return: Returns tuple (longitude, latitude) for given place. Default value for place is New York
        """

        data = {'address': place, 'language': 'en'}
        url = 'https://maps.googleapis.com/maps/api/geocode/json?'
        page = urllib.urlopen(url + urllib.urlencode(data))
        if page.getcode() != 200:
            return None, None
        json_obj = json.load(page)

        return [(result['geometry']['location']['lng'],result['geometry']['location']['lat']) for result in json_obj['results']][0]

    # @lru_cache(maxsize=8)
    def get_time(self, place=None, lat=None, lon=None):
        """Get time information at given place
        """

        # obtain longitude and latitude, if they are not set
        if lat is None and lon is None:
            lon, lat = self.obtain_geo_codes(place)
            # gaining geo location may fail
            if lat is None and lon is None:
                return None, None
        data = {'location': str(lat) + ',' + str(lon),
                'timestamp': int(datetime.utcnow().strftime('%s')),
                'language':'en'}

        self.system_logger.info("GoogleTime request:\n" + ' + ' + str(data))

        page = urllib.urlopen('https://maps.googleapis.com/maps/api/timezone/json?' + urllib.urlencode(data))
        if page.getcode() != 200:
            return None, None
        response = json.load(page)
        self._log_response_json(response)
        time, time_zone = self.parse_time(response)
        self.system_logger.info("GoogleTime response:\n" + unicode(time) + "," + unicode(time_zone))
        return time, time_zone

    def parse_time(self, response):
        time_zone = response[u'timeZoneName']
        offset = response['rawOffset'] + response['dstOffset']
        time = datetime.fromtimestamp(int(datetime.utcnow().strftime("%s")) + offset)
        #int(time.mktime(departure_time.timetuple()))
        return time, time_zone
