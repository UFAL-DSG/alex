#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that creates a compatibility table from a list of stops in a certain city and
its neighborhood and a list of towns and cities.

Usage:

./add_cities_to_stops.py [-d "Main city"] stops.txt cities.txt cities_stops.tsv
"""

from __future__ import unicode_literals
from logging import codecs
import sys
from getopt import getopt

def main():
    opts, files = getopt(sys.argv[1:], 'd:')
    main_city = None
    for opt, arg in opts:
        if opt == '-d':
            main_city = arg

    # sanity check
    if len(files) != 3 or main_city is None:
        sys.exit(__doc__)

    file_stops, file_cities, file_out = files
    cities = set()
    mapping = {}

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
            line = line.strip()
            if "\t" in line:
                line, _ = line.split("\t", 1)
            stop = line
            # stop is a city by itself
            if stop in cities:
                add_to_mapping(stop, stop)
                continue
            # try to split by ',' and '-'
            found = False
            for sepchar in [',', '-', ' u ', ' nad ', ' pod ', 'zastávka', 'město', '{', 'hlavní nádraží', 'hl. n.']:
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


if __name__ == '__main__':
    main()
