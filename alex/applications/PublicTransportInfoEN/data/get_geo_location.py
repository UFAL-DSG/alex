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
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# i needed to install grequests : $ sudo pip install grequests

from __future__ import unicode_literals
import codecs
from getopt import getopt
import os
import sys
import json
import urllib
from time import sleep
from random import random

import grequests

from proxy_list import proxy_list


def build_request(req, proxy='www.webproxy.net:80', protocol='http'):
    return grequests.get(req, proxies={protocol: proxy})


def build_async_batch(req_list, proxy_list):
    # round up batch size
    batch = []
    for i, req in enumerate(req_list):
        request = build_request(req, proxy_list[i])
        batch.append(request)

    return batch


def compose_url(place):
    data = {'address': place, 'language': 'en'}
    url = 'https://maps.googleapis.com/maps/api/geocode/json?' + urllib.urlencode(data)
    return url


def process_batch(requests):
    res = grequests.map(requests)
    results = []
    geo_data = []
    dead_proxies = []
    #TODO: here there should be taken care of proxies, that don't return nothing -> distinguish them and return them along with propper results
    for i, r in enumerate(res):
        try:
            json_obj = json.loads(r.content)
        except Exception:
            print sys.exc_info()[0]
            continue
        if json_obj['status'] != 'OK':
            results.append([])
            dead_proxies.append(requests[i].kwargs['proxies']['http'])
            continue
        long_names = [[x['long_name'] for x in result['address_components'] if 'political' in x['types']] for result in json_obj['results']]
        # flat_set_names = list(set([item for sublist in long_names for item in sublist]))
        results.append(long_names)

        geo = [(result['geometry']['location']['lng'],result['geometry']['location']['lat']) for result in json_obj['results']]
        geo_data.append(geo)

    return results, geo_data, dead_proxies


def process_query(chunk, proxy_list):
    requests = []
    for place in chunk:
        url = compose_url(place)
        requesuts.append(url)
    batch = build_async_batch(requests, proxy_list)

    return process_batch(batch)


# def get_google_name(longitude, latitude):
# """Retrieve (all possible) city names using the Google Geocoding API."""
#     data = {'latlng': ','.join((latitude, longitude,)),
#             'language': 'en'}
#     url = 'https://maps.googleapis.com/maps/api/geocode/json?' + urllib.urlencode(data)
#     page = urllib.urlopen(url)
#     response = json.load(page)
#
#     request = build_async_batch([url, url, url], ["www.webproxy.net:80", "localhost:80"])
#     res = grequests.map(request)
#
#     results = [get_results_from_json(json.loads(r.content)) for r in res]
#     print results[0]
#
#     if not 'results' in response:
#         print >> sys.stderr, '!! Cannot find location:' + ','.join((latitude, longitude))
#
#     # names = [result['formatted_address'] for result in response['results']]
#     long_names = [result['address_components'][0]['long_name'] for result in response['results']]
#     for result in response['results']:
#         # skip non-cities
#         if 'locality' not in result['address_components'][0]['types']:
#             continue
#         # extract district, region and geo-location
#         district = result['address_components'][1]['long_name']
#         region = result['address_components'][2]['long_name']
#         lng = result['geometry']['location']['lng']
#         lat = result['geometry']['location']['lat']
#         # locations.append('|'.join((str(lng), str(lat), district, region)))
#
#     # if len(locations) == 0:
#     #     print >> sys.stderr, ('!! Cannot find city:' + city).encode('utf-8')
#     # else:
#     #     print >> sys.stderr, (city + (' found [%dx].' % len(locations))).encode('utf-8')
#     return long_names[4]


def get_column_index(header, caption, default):
    for i, h in enumerate(header.strip().split(',')):
        if h == caption:
            return i
    return default


def extract_fields(lines, header):
    stop_index = get_column_index(header, "stop_name", 2)
    lat_index = get_column_index(header, "stop_lat", 4)
    lon_index = get_column_index(header, "stop_lon", 5)

    stops = []
    geo_data = []

    for line in lines:
        if line.startswith('#') or not line:
            continue;
        fields = line.strip().split(',')
        if fields[stop_index].startswith('"') and not fields[stop_index].endswith('"'):
            stop = fields[stop_index] + ',' + fields[stop_index + 1]
            stop.strip('"')
            latitude = fields[lat_index+1].strip().strip('"')
            longitude = fields[lon_index+1].strip().strip('"')
        else:
            stop = fields[stop_index].strip('"')
            latitude = fields[lat_index].strip().strip('"')
            longitude = fields[lon_index].strip().strip('"')

        stops.append(stop)
        geo_data.append((longitude, latitude))
    return (geo_data, stops)

def get_chunk(buf, previously_processed,  n):
    """ Read n-line chunks from filehandle. Returns sequence of n lines, or None at EOF.
        it skips any stop that was previously processed
    """

    chunk = []
    while len(chunk) < n:
        in_line = buf.readline().strip()
        if not in_line:
            return chunk
        place = in_line.strip()
        if place in previously_processed:
            continue;
        chunk.append(in_line)

    return chunk


def find_locations(file_in, file_out, proxy_list, delay = 1, chunk_size = 55):

    with codecs.open(file_in, 'r', 'UTF-8') as fs_in:
        num_records = 0
        previously_processed = load_reference_file(file_out)
        print str(len(previously_processed)) + " previously processed:"

        with codecs.open(file_out, 'a', 'UTF-8') as fs_out:
            chunk_rest = []
            proxies_in_use = []
            while chunk_rest is not None:
                chunk = get_chunk(fs_in, previously_processed, chunk_size - len(chunk_rest))
                # append previously non-successful lines
                chunk = chunk_rest + chunk
                # end of input file handling
                if not chunk:
                    break
                if len(proxies_in_use) < len(chunk):
                    proxies_in_use.extend(list(proxy_list))

                possible_names, geo_data, dead_proxies = process_query(chunk, proxies_in_use)
                proxies_in_use = [proxy for proxy in proxies_in_use if proxy not in dead_proxies]

                # handle non-successful queries

                chunk_rest = [chunk[i] for i, names in enumerate(possible_names) if not names]
                if chunk_rest is None:
                    print "not chunk_rest"
                chunk = [chunk[i] for i, names in enumerate(possible_names) if names]

                # geo_data = [geo_data[i] for i, names in enumerate(possible_names) if names]
                possible_names = [names for names in possible_names if names]

                # ref_city_match = []
                # for options in possible_names:
                #     match = []
                #     for name in options:
                #         if name in ref_city_list:
                #             match.append(name)
                #     if not match:
                #         match = options
                #     ref_city_match.append(match)

                output_lines = [ch + '\t' + ';'.join(l) + '\t' + ';'.join(str(geo[i]).strip('(').strip(')').split(',')) + '\n' for (ch, loc,geo) in zip(chunk, possible_names, geo_data) for i,l in enumerate(loc)]
                num_records += len(output_lines)

                fs_out.writelines(output_lines)

                print str(len(output_lines)) + " out of " + str(len(chunk)) + " has succeeded, " + str(num_records) + ' processed; ' + str(len(proxies_in_use)) + " proxies left"
                sleep(delay + 0.2 * random() * delay)

#
# Main
#

def load_reference_file(file_name):
    """ Reads first field from file and returns it as a list. Fields are separated by tabs.
        If ref_state (abbreviated) is specified, it only returns cities in that state
    """
    ref_list = []
    with codecs.open(file_name, 'r', 'UTF-8') as fs_ref:
        for line in fs_ref:
            if line.startswith('#'):
                continue
            first_field = line.strip().split('\t', 1)[0]
            ref_list.append(first_field)
    return ref_list

if __name__ == '__main__':

    _, files = getopt(sys.argv[1:],[])
    # sanity check
    if len(files) != 2:
        sys.exit(__doc__)

    file_in, file_out = files

    if not os.path.isfile(file_out):
        open(file_out, 'w').close()

    find_locations(file_in, file_out, proxy_list)
