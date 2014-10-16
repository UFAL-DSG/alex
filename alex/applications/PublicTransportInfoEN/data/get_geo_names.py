#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that collects the location names (city, state) of all the given longitude, latitude coordinates using the Google Geocoding API.

Usage:

./get_geo_names.py [-d delay] [-l limit] [-a] locations-in.tsv names-out.tsv

-d = delay between requests in seconds (will be extended by a random period up to 1/2 of the original value)
-l = limit maximum number of requests
-a = retrieve all locations, even if they are set
"""

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
import math

import grequests


def get_results_from_json(r):
    try:
        json_obj = json.loads(r.content)
    except Exception:
        print sys.exc_info()[0]
        return []
    political_lists = [result['address_components'] for result in json_obj['results'] if 'political' in result['types']]
    #todo add only political places -> these are cities (there are county and district, which could be interresting...)
    long_names = [[x['long_name'] for x in result['address_components'] if 'political' in x['types']] for result in json_obj['results']]
    flat_set_names = list(set([item for sublist in long_names for item in sublist]))
    return flat_set_names


def build_requests(req_list, proxy='www.webproxy.net:80', protocol='http'):
    requests = [grequests.get(req, proxies={protocol: proxy}) for req in req_list]
    return requests


def build_async_batch(req_list, proxy_list):
    # round up batch size
    batch_size = int(math.ceil(float(len(req_list)) / len(proxy_list)))
    batch = []

    for proxy in proxy_list:
        if not req_list:
            break
        tail = min(len(req_list), batch_size)
        req_batch = req_list[0:tail]
        req_list = req_list[tail:]

        requests = build_requests(req_batch, proxy)
        batch.extend(requests)

    return batch


def compose_url(longitude, latitude):
    data = {'latlng': ','.join((latitude, longitude,)), 'language': 'en'}
    url = 'https://maps.googleapis.com/maps/api/geocode/json?' + urllib.urlencode(data)
    return url


def process_batch(requests):
    res = grequests.map(requests)
    results = [get_results_from_json(r) for r in res]
    return results


def process_query(chunk, proxy_list):
    requests = []
    for (lon, lat) in chunk:
        url = compose_url(lon, lat)
        requests.append(url)
    batch = build_async_batch(requests, proxy_list)
    results = process_batch(batch)
    return results


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
    for i, h in enumerate(header.split(',')):
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
        stop = fields[stop_index].strip('"')
        latitude = fields[lat_index].strip()
        longitude = fields[lon_index].strip()

        stops.append(stop)
        geo_data.append((longitude, latitude))
    return (geo_data, stops)

def get_chunk(buf, in_file_header, previously_processed,  n):
    """ Read n-line chunks from filehandle. Returns sequence of n lines, or None at EOF.
        it skips any stop that was previously processed
    """

    chunk = []
    while len(chunk) < n:
        in_line = buf.readline()
        if not in_line:
            return chunk
        stop_index = get_column_index(in_file_header, "stop_name", 2)
        stop = in_line.strip().split(',')[stop_index].strip('"')
        if stop in previously_processed:
            continue;
        chunk.append(in_line)

    if not any(chunk):  # detect end-of-file (list of ['', '',...] )
        chunk = None

    return chunk


def find_names(file_in, file_out, proxy_list, limit, req_per_sec=5, delay = 1, proxy_batch_size = 50):
    chunk_size = proxy_batch_size * req_per_sec

    with codecs.open(file_in, 'r', 'UTF-8') as fs_in:
        header = fs_in.readline()
        num_records = 0
        previously_processed = load_reference_file(file_out)

        with codecs.open(file_out, 'a', 'UTF-8') as fs_out:
            chunk_rest = []
            dead_proxies = []
            proxy_batch = []

            while num_records < limit:
                chunk = get_chunk(fs_in, header, previously_processed, chunk_size - len(chunk_rest))
                # end of input file handling
                if not chunk:
                    break

                print "chunk size: " + str(len(chunk)) + " rest: " + str(len(chunk_rest))
                pb_length = proxy_batch_size - len(proxy_batch)
                proxy_batch.extend([proxy for proxy in proxy_list if not proxy in dead_proxies and not proxy in proxy_batch][:pb_length])
                if len(proxy_batch) != pb_length:
                    dead_proxies = []
                    proxy_batch.extend([proxy for proxy in proxy_list if not proxy in dead_proxies and not proxy in proxy_batch][:pb_length])

                # append previously non-successful lines
                chunk = chunk_rest + chunk
                # preprocess chunk of lines
                geo_data, stops = extract_fields(chunk, header)
                # list of names for each entry

                possible_names = process_query(geo_data, proxy_batch)
                # handle non-successful queries
                chunk_rest = [chunk[i] for i, names in enumerate(possible_names) if not names]

                geo_data = [geo_data[i] for i, names in enumerate(possible_names) if names]
                stops = [stops[i] for i, names in enumerate(possible_names) if names]


                proxy_batch_succ = [proxy_batch[i/req_per_sec] for i, names in enumerate(possible_names) if names]
                proxy_batch_succ = list(set((proxy_batch_succ)))
                # dead_proxies = [proxy_batch[i/req_per_sec] for i, names in enumerate(possible_names) if not names] + dead_proxies
                dead_proxies = [dead for dead in proxy_batch if dead not in proxy_batch_succ] + dead_proxies
                dead_proxies = list(set((dead_proxies)))
                proxy_batch = proxy_batch_succ

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

                output_lines = [stop + '\t' + ';'.join(names) + '\t' + ';'.join(geo) + '\n' for stop, names, geo in zip(stops, possible_names, geo_data)]
                num_records += len(output_lines)

                fs_out.writelines(output_lines)

                print str(len(chunk_rest)) + " out of " + str(chunk_size) + " has failed, " + str(num_records) + ' processed'
                sleep(delay + 0.5 * random() * delay)

#
# Main
#

def load_reference_file(file_name, ref_state = None):
    """ Reads first field from file and returns it as a list. Fields are separated by tabs.
        If ref_state (abbreviated) is specified, it only returns cities in that state
    """
    ref_list = []
    with codecs.open(file_name, 'r', 'UTF-8') as fs_ref:
        for line in fs_ref:
            if line.startswith('#'):
                continue
            first_field = line.strip().split('\t', 1)[0]
            # if state is specified skip non matching states
            if ref_state and not ref_state == line.strip().split("|")[-1]:
                continue;

            ref_list.append(first_field)
    return ref_list

if __name__ == '__main__':

    _, files = getopt(sys.argv[1:],[])
    # sanity check
    if len(files) != 2:
        sys.exit(__doc__)

    limit = 3000


    proxy_list = [

# "115.236.59.194:3128",
# "200.98.239.131:443",
# "218.108.170.164:80",
# "46.165.193.67:9620",
# "221.10.102.199:81",
# "196.201.217.49:4011",
# "180.169.23.140:80",
# "182.92.105.140:8888",
# "120.203.214.182:83",
# "112.96.28.46:80",
# "211.167.105.104:82",
# "190.102.11.205:80",
# "183.159.3.2:8088",
# "211.143.146.239:80",
# "194.247.12.11:6351",
# "196.201.217.48:4015",
# "137.135.166.225:8123",
# "92.109.157.80:80",
# "111.13.109.52:80",
# "196.201.217.49:4009",
# "171.8.249.45:8118",
# "122.96.59.107:81",
# "91.209.67.97:8080",
# "60.164.144.228:8585",
# "112.124.30.44:808",
# "194.247.12.11:5628",
# "117.79.64.84:80",
# "62.210.237.175:80",
# "149.255.255.242:80",
# "196.201.217.49:80",
# "120.203.214.144:80",
# "196.201.217.48:4010",
# "196.201.217.49:4012",
# "196.201.217.48:80",
# "123.155.253.207:80",
# "122.96.59.104:80",
# "196.201.217.49:4006",
# "111.13.87.173:8081",
# "220.133.46.192:1080",
# "115.228.60.254:80",
# "46.165.193.67:6391",
# "120.203.214.147:83",
# "149.255.255.250:80",
# "202.52.11.74:8080",
# "41.32.167.91:8080",
# "61.50.245.163:8000",
# "42.121.82.151:1080",
# "111.13.109.54:80",
# "183.141.79.4:80",
# "106.187.89.72:443",

        # "ciproxy.de:80",
        # "http://free-proxyserver.com/:80",
        # "196.201.217.48:4014",#HTTP
        # "110.164.65.19:8080",#HTTP
        # "218.108.170.162:82",#HTTP
        # "222.87.129.30:80",#HTTP
        # "124.206.241.214:8118",#HTTP
        # "200.99.150.70:8080",#HTTP
        # "176.31.99.16:3128",#HTTP
        # "115.228.56.200:80",#HTTP
        # "59.46.66.244:808",#HTTP
        # "111.13.109.26:81",#HTTP
        # "210.101.131.231:8080",#HTTP
        # "61.50.245.163:8888",#HTTP
        # "61.50.245.163:8000",#HTTP
        # "122.232.227.18:80",#HTTP
        # "203.192.12.148:80",#HTTP
        # "183.141.75.98:80",#HTTP
        # "183.141.64.170:80",#HTTP
        # "183.230.53.146:8123",#HTTP
        # "202.152.6.10:8080",#HTTP
        # "218.108.170.163:82",#HTTP
        # "120.203.214.182:84",#HTTP
        # "61.234.123.64:8080",#HTTPS
        # "201.243.112.105:8080",#HTTPS
        # "183.221.160.19:8123",#HTTPS
        # "118.70.177.90:8888",#HTTPS
        # "78.188.3.171:8080",#HTTPS
        # "123.30.59.179:3128",#HTTPS
        # "190.204.111.245:8080",#HTTPS
        # "200.110.32.56:8080",#HTTPS
        # "186.88.96.55:8080",#HTTPS
        # "64.31.22.131:7808",#HTTPS
        # "184.164.77.109:3127",#HTTPS
        # "87.229.89.40:3128",#HTTPS
        # "89.232.139.253:80",#HTTPS
        # "110.77.196.242:3128",#HTTPS
        # "218.204.131.250:3128",#HTTPS
        # "121.10.252.139:3128",#HTTPS
        # "183.230.53.168:8123",#HTTPS
        # "190.198.31.176:8080",#HTTPS
        # "190.201.106.165:8080",#HTTPS
        # "188.40.252.215:7808",#HTTPS
        # "202.56.203.150:80",#HTTPS
        # "186.93.233.248:8080",#HTTPS
        # "190.206.153.31:8080",#HTTPS
        # "209.170.151.142:8089",#HTTPS
        # "183.221.170.135:8123",#HTTPS
        # "115.124.74.14:3128",#HTTPS
        # "183.89.94.139:3128",#HTTPS
        # "195.112.240.46:1080",#socks4/5
        # "92.27.232.170:52959",#socks4/5
        # "proxyguru.info:80",
        # "igotswagproxy.info:80",
        # "newfreeproxy.com:80",
        # "free.unblockyoutuber.com:80",
        # "igo.copih.com:80",
        # "cashadproxy.info:80",
        # "sc.copih.com:80",
        # "anony-surf.info:80",
        # "cproxy.ga:80",
        # "rexoss.com:80",
        # "ccproxy.pw:80",
        # "speedestproxyz.info:80",
        # "proxysrapides.info:80",
        # "free-proxysite.com:80",
        # "p12p.com:80",
        # "bestproxy4free.ml:80",
        # "crecipes.info:80",
        # "usc.proxygogo.info:80",
        # "goodcore.ga:80",
        # "online.hidevpn.asia:80",
        # "wowevent.net:80",
        # "52ufo.org:80",
        # "proxy4free.cf:80",
        # "school.unblockyoutuber.com:80",
        # "new.2r34.com:80",
        # "ppproxy.pw:80",
        # "zzz.vtunnelwebproxy.info:80",
        # "gt.unblockyoutuber.com:80",
        # "gto.copih.com:80",
        # "llproxy.pw:80",
        # "usprxy.com:80",
        # "easyhideip.org:80",
        # "abc.a-tunnel.info:80",
        # "rrproxy.pw:80",
        # "eeuu.free4proxy.tv:80",
        # "proxyceo.ga:80",
        # "waproxy.com:80",
        # "c1.yunproxy.org:80",
        # "websurf.in:80",
        # "watchyoutube.pw:80",
        # "usc.proxyhash.info:80",
        # "stripproxy.info:80",
        # "heyproxy.com:80",
        # "unblockwebsites.us:80",
        # "abcdproxy.info:80",
        # "proxyhash.info:80",
        # "ioxy.de:80",
        # "url10.org:80",
        # "gomko.net:80",
        # "proxyzan.info:80",
        # "mybabyprox.info:80",
        # "france.proxy8.asia:80",
        # "the-best-of-proxy.info:80",
        # "gofollow.info:80",
        # "us.newproxy.pw:80",
        # "spin.copih.com:80",
        # "french-proxy.info:80",
        # "topsiteproxy.info:80",
        # "bypass.1proxy.in:80",
        # "fast.proxy.com.de:80",
        # "ninjaproxyserver.com:80",
        # "webbee.info:80",
        # "ske.profliste.com:80",
        # "proxyok.com:80",
        # "sure.unblockyoutuber.com:80",
        # "comboproxy.info:80",
        # "urproxy.ga:80",
        "fi.copih.com:80",
        "123abcproxy.ml:80",
        "hotlap.ml:80",
        "free-proxy-online.com:80",
        "surf-anonymously.com:80",
        "bip.copih.com:80",
        "proxy4youtube.info:80",
        "fastpage.info:80",
        "faster.proxy.yt:80",
        "isportmagz.com:80",
        "iproxysite.com:80",
        "youtube-proxy.co:80",
        "ag.unblockyoutuber.com:80",
        "proxy.wiksa.com:80",
        "proxytroprapide.info:80",
        "thisisgoodshit.info:80",
        "kkproxy.pw:80",
        "foxsiteoneproxy.com:80",
        "hide.copih.com:80",
        "emergency-proxy.info:80",
        "aaproxy.pw:80",
        "proxyhub.eu:80",
        "faboroxy.com:80",
        "52ufo.org:80",
        "creativeproxy.info:80",
        "hhproxy.pw:80",
        "a.unblockyoutuber.com:80",
        "proxyceo.ga:80",
        "proxy4free.pl:80",
        "gofollow.info:80",
        "012ooo.proxyserver.asia:80",
        "sc.profliste.com:80",
        "school.unblockyoutuber.com:80",
        "free-proxy-online.com:80",
        "www.webproxy.net:80",
        "ciproxy.de:80",
        "pl.copih.com:80",
        "petsecure.info:80",
        "fastpage.info:80",
        "fast.unblockyoutuber.com:80",
        "california-proxy.info:80",
        "3rd-party.org.uk:80",
        "neo.profliste.com:80",
        "proxyfreeweb.com:80",
        "easyhideip.org:80",
        "anony-surf.info:80",
        "bip.copih.com:80",
        "unblockwebsites.us:80",
        "sassygayguyprox.info:80",
        "cashadproxy.info:80",
        "heinz-proxy.info:80",
        "hourra-hourra.info:80",
        "bywork.ga:80",
        "wowevent.net:80",
        "freevps.biz:80",
        "tit.copih.com:80",
        "proxystreaming.com:80",
        "llproxy.pw:80",
        "easysurf.info:80",
        "faboroxy.com:80",
        "proxy-de-france.net:80",
        "proxytroprapide.info:80",
        "new.2r34.com:80",
        "proxy4free.cf:80",
        "sslproxy.in:80",
        "bywork.ga:80",
        "777speed.info:80",
        "angele-proxy.info:80",
        "timeplacesproxy.info:80",
        "thebestofproxy.info:80",
        "freevps.biz:80",
        "petsecure.info:80",
        "free.copih.com:80",
        "0-proxy.info:80",
        "easyth3.appspot.com:80",
        "easy.unblockyoutuber.com:80",
        "gofollow.fr:80",
        "ghostproxy.nl:80",
        "bbproxy.pw:80",
        "ni.profliste.com:80",
        # "web.securesurf.pw:80",
        # "hd.unblockyoutuber.com:80",
        # "012ooo.proxyserver.asia:80",
        # "neo.profliste.com:80",
        # "northamericanproxy.com:80",
        # "jezuslovesthisproxy.info:80",
        # "secure-reliable-proxy.info:80",
        # "proxyceo.ml:80",
        # "yaproxy.com:80",
        # "sassygayguyprox.info:80",
        # "usproxy.pw:80",
        # "bk.copih.com:80",
        # "proxyinc.info:80",
        # "goodcore.cf:80",
        ]
    proxy_list = list(set(proxy_list))

    file_in, file_out = files

    if not os.path.isfile(file_out):
        open(file_out, 'w').close()

    find_names(file_in, file_out, proxy_list, limit)
