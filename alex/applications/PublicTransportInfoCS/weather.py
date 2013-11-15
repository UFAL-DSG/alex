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


class Weather(object):
    pass


class OpenWeatherMapWeather(Weather):

    def __init__(self, input_json):
        self.temp = int(round(input_json['main']['temp'] - 273.15))
        self.condition = input_json['weather'][0]['description']


class WeatherFinder(object):
    """Abstract ancestor for transit direction finders."""

    def get_weather(self, time=None):
        """
        Retrieve the weather for the given time, or for now (if time is None).

        Should be implemented in derived classes.
        """
        raise NotImplementedError()


class OpenWeatherMapWeatherFinder(WeatherFinder):
    """Transit direction finder using the Google Maps query engine."""

    CONDITION_TRANSL = {}

    def __init__(self, cfg):
        super(WeatherFinder, self).__init__()
        self.system_logger = cfg['Logging']['system_logger']
        self.session_logger = cfg['Logging']['session_logger']
        self.weather_url = 'http://api.openweathermap.org/data/2.5/'


    def get_weather(self, time=None):
        """Get OpenWeatherMap weather information or forecast for the given time.

        The time/date should be given as a datetime.datetime object.
        """
        data = {
            'q': 'Prague,CZE',
            'lang': 'cz'
        }
        method = 'forecast' if time is not None else 'weather'

        self.system_logger.info("OpenWeatherMap request:\n" + str(data))

        page = urllib.urlopen(self.weather_url + method + '?' + urllib.urlencode(data))
        response = json.load(page)
        self._log_response_json(response)
        print response
        weather = OpenWeatherMapWeather(response)
        self.system_logger.info("OpenWeatherMap response:\n" + unicode(weather))
        return weather

    def _log_response_json(self, data):
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f')
        fname = os.path.join(self.system_logger.get_session_dir_name(),
                             'openweathermap-{t}.json'.format(t=timestamp))
        fh = codecs.open(fname, 'w', 'UTF-8')
        json.dump(data, fh, indent=4, separators=(',', ': '),
                  ensure_ascii=False)
        fh.close()
        self.session_logger.external_data_file('OpenWeatherMap query', os.path.basename(fname))
