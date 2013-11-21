#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from logging import codecs
import sys


if len(sys.argv) != 4:
    sys.exit('Usage: ./add_cities_to_stops.py stops.txt cities.txt cities_stops.txt')

file_stops, file_cities, file_out = sys.argv[1:]
cities = set()
mapping = {}
#stderr = codecs.getwriter('UTF-8')(sys.stderr)

with codecs.open(file_cities, 'r', 'UTF-8') as fh_in:
    for line in fh_in:
        line = line.strip()
        cities.add(line)


def add_to_mapping(city, stop):
    entry = mapping.get(city, set())
    entry.add(stop)
    mapping[city] = entry

with codecs.open(file_stops, 'r', 'UTF-8') as fh_in:
    for line in fh_in:
        stop = line.strip()
        # stop is a city by itself
        if stop in cities:
            add_to_mapping(stop, stop)
            continue
        # try to split by ',' and '-'
        found = False
        for sepchar in [',', '-', ' u ', ' nad ', ' pod ', 'zastávka', 'město', '{']:
            if sepchar in stop:
                prefix, suffix = [x.strip() for x in line.split(sepchar, 1)]
                if prefix in cities:
                    add_to_mapping(prefix, stop)
                    found = True
                    break
        if found:
            continue
        # fallback to Prague
        add_to_mapping('Praha', stop)

with codecs.open(file_out, 'w', 'UTF-8') as fh_out:
    for city in sorted(mapping.keys()):
        for stop in sorted(mapping[city]):
            print >> fh_out, city + "\t" + stop
