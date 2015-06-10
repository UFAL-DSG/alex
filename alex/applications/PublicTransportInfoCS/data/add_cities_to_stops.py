#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that creates a compatibility table from a list of stops in a certain city and
its neighborhood and a list of towns and cities.

Usage:

./add_cities_to_stops.py [-d "Main city"] stops.txt cities.txt cities_stops.tsv
"""

from __future__ import unicode_literals
import codecs
import sys
from getopt import getopt


def load_list(filename, suppress_comments=False, cols=1):
    data = []
    with codecs.open(filename, 'r', 'UTF-8') as fh_in:
        for line in fh_in:
            line = line.strip()
            # handle comments (strip or skip)
            if line.startswith('#'):
                if suppress_comments:
                    line = line.lstrip('#')
                else:
                    continue
            # handle columns -- convert to arrays, delete superfluous
            line = line.split("\t")
            line = line[:cols]
            if len(line) == 1:
                data.append(line[0])
            else:
                data.append(line)
    return data


def get_city_for_stop(cities, stop, main_city):
    # stop is a city by itself
    if stop in cities:
        return stop
    # try to split by ',' and '-' + some names occurring in train stops where no punctuation is used
    for sepchar in [',', '-', ';', ' u ', ' nad ', ' pod ', ' v ', ' ve ', 'zastávka', 'město', '{', '[', '/',
                    'hlavní nádraží', 'hl. n.', ' na ', 'klášter', 'obec', 'severní', 'jižní', 
                    'západ', 'východ', 'jih', 'sever', 'západní', 'východní', 'centrum',
                    'střed', 'zámecká zahrada', 'zálesí', 'kolonie', 'lázně', 'hlavní',
                    'střelnice', 'bazén', 'koupaliště', 'předměstí', 'místní', 'zámek',
                    'horní', 'dolní', 'Cihelna', 'jeskyně', 'dílny', 'rybník', 'bažantnice', 'nemocnice',
                    'Masarykovo', 'jedna', 'dvě', 'závod', 'obec']:
        if sepchar in stop:
            prefix, suffix = [x.strip() for x in stop.split(sepchar, 1)]
            if prefix in cities:
                return prefix
            # city is separated by a '/' (after city part)
            if sepchar == '/':
                city = get_city_for_stop(cities, suffix, None)
                if city is not None:
                    return city
    # fallback to main city or store in list of unresolved
    if main_city is not None:
        return main_city
    else:
        return None


def add_cities_to_stops(cities, stops, main_city):

    mapping = {}
    unresolved = []

    def add_to_mapping(city, stop):
        entry = mapping.get(city, set())
        entry.add(stop)
        mapping[city] = entry

    # process list of stops
    for stop in stops:
        city = get_city_for_stop(cities, stop, main_city)
        if city:
            add_to_mapping(city, stop)
        else:
            unresolved.append(stop)
    # return the result
    return mapping, unresolved


def main():
    opts, files = getopt(sys.argv[1:], 'd:')
    main_city = None
    for opt, arg in opts:
        if opt == '-d':
            main_city = arg

    # sanity check
    if len(files) != 3:
        sys.exit(__doc__)

    # initialization
    file_stops, file_cities, file_out = files
    stderr = codecs.getwriter('UTF-8')(sys.stderr)

    # load list of cities
    cities = set(load_list(file_cities, suppress_comments=True))
    # load list of stops
    stops = load_list(file_stops, cols=1)

    mapping, unresolved = add_cities_to_stops(cities, stops, main_city)

    # write the result
    with codecs.open(file_out, 'w', 'UTF-8') as fh_out:
        for city in sorted(mapping.keys()):
            for stop in sorted(mapping[city]):
                print >> fh_out, city + "\t" + stop

    # print any errors
    if unresolved:
        print >> stderr, 'Could not resolve:'
        for stop in unresolved:
            print >> stderr, stop

if __name__ == '__main__':
    main()
