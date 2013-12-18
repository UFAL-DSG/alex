#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that collects the locations of all the given cities using the Google
Geocoding API.

Usage:

./get_cities_locations.py [-d delay] [-l limit] [-a] cities_locations-in.tsv cities_locations-out.tsv

-d = delay between requests in seconds (will be extended by a random period
        up to 1/2 of the original value)
-l = limit maximum number of requests
-a = retrieve all locations, even if they are set
"""


from __future__ import unicode_literals
import codecs
import sys
from getopt import getopt
import json
import urllib
from time import sleep
from random import random


def get_google_coords(city):
    """Retrieve (all possible) coordinates of a city using the Google Geocoding API."""
    data = {'sensor': 'false',
            'address': ('"obec %s",Czech Republic' % city).encode('utf-8'),
            'language': 'cs'}
    page = urllib.urlopen('http://maps.googleapis.com/maps/api/geocode/json?' +
                          urllib.urlencode(data))
    response = json.load(page)
    if not 'results' in response:
        print >> sys.stderr, '!! Cannot find city:' . city.encode('utf-8')

    locations = []
    for loc in response['results']:
        # skip non-cities
        if 'locality' not in loc['address_components'][0]['types']:
            continue
        # extract district, region and geo-location
        district = loc['address_components'][1]['long_name']
        region = loc['address_components'][2]['long_name']
        lng = loc['geometry']['location']['lng']
        lat = loc['geometry']['location']['lat']
        locations.append('|'.join((str(lng), str(lat), district, region)))

    if len(locations) == 0:
        print >> sys.stderr, ('!! Cannot find city:' + city).encode('utf-8')
    else:
        print >> sys.stderr, (city + (' found [%dx].' % len(locations))).encode('utf-8')

    return locations

#
# Main
#

if __name__ == '__main__':

    # parse options
    opts, files = getopt(sys.argv[1:], 'd:l:a')
    delay = 5
    limit = 100
    override_all = False
    for opt, arg in opts:
        if opt == '-d':
            delay = int(arg)
        elif opt == '-l':
            limit = int(arg)
        elif opt == '-a':
            override_all = True

    # sanity check
    if len(files) != 2:
        sys.exit(__doc__)

    file_in, file_out = files

    requests = 0
    with codecs.open(file_in, 'r', 'UTF-8') as fh_in:
        with codecs.open(file_out, 'w', 'UTF-8') as fh_out:
            for line in fh_in:
                line = line.strip()
                # check if there are coordinates already
                if (not override_all and '\t' in line) or (requests > limit):
                    print >> fh_out, line
                    continue
                if line.startswith('#'):  # also work with commented-out cities
                    line = line[1:]
                line = line.split('\t', 1)[0]  # strip previous coordinates, if applicable
                try:
                    coords = get_google_coords(line)
                    print >> fh_out, line + '\t' + '\t'.join(coords)
                except:
                    print >> sys.stderr, ('!!ERROR:' + str(e) + ' -- cannot find city:' + line).encode('utf-8')
                    print >> fh_out, line
                requests += 1
                sleep(delay + 0.5 * random() * delay)
