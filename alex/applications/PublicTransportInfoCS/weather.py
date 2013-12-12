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


class Weather(object):
    pass


class OpenWeatherMapWeather(Weather):

    CONDITION_TRANSL = {200: 'bouřka se slabým deštěm',
                        201: 'bouřka a déšť',
                        202: 'bouřka se silným deštěm',
                        210: 'slabší bouřka',
                        211: 'bouřka',
                        212: 'silná bouřka',
                        221: 'bouřková přeháňka',
                        230: 'bouřka se slabým mrholením',
                        231: 'bouřka s mrholením',
                        232: 'bouřka se silným mrholením',
                        300: 'slabé mrholení',
                        301: 'mrholení',
                        302: 'silné mrholení',
                        310: 'slabé mrholení a déšť',
                        311: 'mrholení s deštěm',
                        312: 'silné mrholení a déšť',
                        313: 'mrholení a přeháňky',
                        314: 'mrholení a silné přeháňky',
                        321: 'občasné mrholení',
                        500: 'slabý déšť',
                        501: 'déšť',
                        502: 'prudký déšť',
                        503: 'přívalový déšť',
                        504: 'průtrž mračen',
                        511: 'mrznoucí déšť',
                        520: 'slabé přeháňky',
                        521: 'přeháňky',
                        522: 'silné přeháňky',
                        531: 'občasné přeháňky',
                        600: 'mírné sněžení',
                        601: 'sněžení',
                        602: 'husté sněžení',
                        611: 'zmrzlý déšť',
                        612: 'smíšené přeháňky',
                        615: 'slabý déšť se sněhem',
                        616: 'déšť se sněhem',
                        620: 'slabé sněhové přeháňky',
                        621: 'sněhové přeháňky',
                        622: 'silné sněhové přeháňky',
                        701: 'mlha',
                        711: 'kouř',
                        721: 'opar',
                        731: 'písečné či prachové víry',
                        741: 'hustá mlha',
                        751: 'písek',
                        761: 'prašno',
                        762: 'sopečný popel',
                        771: 'prudké bouře',
                        781: 'tornádo',
                        800: 'jasno',
                        801: 'skoro jasno',
                        802: 'polojasno',
                        803: 'oblačno',
                        804: 'zataženo',
                        900: 'tornádo',
                        901: 'tropická bouře',
                        902: 'hurikán',
                        903: 'zima',
                        904: 'horko',
                        905: 'větrno',
                        906: 'krupobití',
                        950: 'bezvětří',
                        951: 'vánek',
                        952: 'větřík',
                        953: 'slabý vítr',
                        954: 'mírný vítr',
                        955: 'čerstvý vítr',
                        956: 'silný vítr',
                        957: 'prudký vítr',
                        958: 'bouřlivý vítr',
                        959: 'vichřice',
                        960: 'silná vichřice',
                        961: 'mohutná vichřice',
                        962: 'orkán'}

    def __init__(self, input_json, time=None, daily=False):
        # get current weather
        if time is None:
            self.temp = self._round_temp(input_json['main']['temp'])
            self.condition = self.CONDITION_TRANSL[input_json['weather'][0]['id']]
            return
        # get prediction
        if daily:  # set time to 13:00 for daily
            time = datetime.combine(time.date(), dttime(13, 00))
        ts = int(time.strftime("%s"))  # convert time to Unix timestamp
        for fc1, fc2 in zip(input_json['list'][:-1], input_json['list'][1:]):
            # find the appropriate time frame
            if ts >= fc1['dt'] and ts <= fc2['dt']:
                self.condition = self.CONDITION_TRANSL[fc1['weather'][0]['id']]
                # hourly forecast -- interpolate temperature
                if not daily:
                    slope = (fc2['main']['temp'] - fc1['main']['temp']) / (fc2['dt'] - fc1['dt'])
                    self.temp = self._round_temp(fc1['main']['temp'] + slope * (ts - fc1['dt']))
                # daily forecast: use daily high & low
                else:
                    self.temp = self._round_temp(fc1['temp']['day'])
                    self.min_temp = self._round_temp(fc1['temp']['min'])
                    self.max_temp = self._round_temp(fc1['temp']['max'])

    def _round_temp(self, temp):
        return int(round(temp - 273.15))

    def __repr__(self):
        ret = self.condition + ', '
        if hasattr(self, 'min_temp'):
            ret += str(self.min_temp) + ' – ' + str(self.max_temp)
        else:
            ret += str(self.temp)
        return ret + ' °C'


class WeatherFinder(object):
    """Abstract ancestor for transit direction finders."""

    def get_weather(self, time=None, daily=False, place=None):
        """
        Retrieve the weather for the given time, or for now (if time is None).

        Should be implemented in derived classes.
        """
        raise NotImplementedError()


class OpenWeatherMapWeatherFinder(WeatherFinder, APIRequest):
    """Weather service using OpenWeatherMap (http://openweathermap.org)"""

    def __init__(self, cfg):
        WeatherFinder.__init__(self)
        APIRequest.__init__(self, cfg, 'openweathermap', 'OpenWeatherMap query')
        self.weather_url = 'http://api.openweathermap.org/data/2.5/'

    def get_weather(self, time=None, daily=False, place=None):
        """Get OpenWeatherMap weather information or forecast for the given time.

        The time/date should be given as a datetime.datetime object.
        """
        # default to weather for Czech Rep.
        place = place if place is not None else 'Czech Republic'
        # set the place
        data = {
            'q': (place + ',CZ').encode('utf-8'),
        }
        method = 'weather'
        if daily:
            method = 'forecast/daily'
        elif time is not None:
            method = 'forecast'

        self.system_logger.info("OpenWeatherMap request:\n" + method + ' + ' + str(data))

        page = urllib.urlopen(self.weather_url + method + '?' + urllib.urlencode(data))
        if page.getcode() != 200:
            return None
        response = json.load(page)
        self._log_response_json(response)
        weather = OpenWeatherMapWeather(response, time, daily)
        self.system_logger.info("OpenWeatherMap response:\n" + unicode(weather))
        return weather
