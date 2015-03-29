#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that creates an expansion from a preprocessed list of cities

For usage write expand_cities_script.py -h
"""

from __future__ import unicode_literals
from optparse import OptionParser
from collections import defaultdict
import autopath
import sys

from alex.applications.PublicTransportInfoEN.data.expand_stops_script import handle_csv, read_expansions, \
    read_first_column, merge, append, save_out


def all_to_lower(site_list):
    sites = defaultdict(list)

    for site in site_list:
        sites[site] = [site.lower(),]
    return sites


def handle_cities(cities_in, cities_out, cities_append, no_cache=False):
    # currently expanded cities
    if no_cache:
        prev = {}
    else:
        prev = read_expansions(cities_out)
    # manually added expansions of specific cities not covered by automatic expansion
    manual_expansions = {} if cities_append is None else read_expansions(cities_append)
    # new expanded cities
    expanded = all_to_lower(read_first_column(cities_in))
    # merged new and old expansions, old ones have greater priority (no appending)
    merged = merge(prev, expanded)
    # add manual expansions to automatic ones
    append(merged, manual_expansions)
    # save it all
    save_out(cities_out, merged)


def main():
    city_out = "./cities.expanded.txt"
    geo_out = "./cities.locations.csv"
    # compatibility_out = "./state.city.txt"
    
    parser = OptionParser()
    parser.add_option("--cities", metavar="CITY_FILE", help="read input cities from CITY_FILE")
    parser.add_option("--append-cities", metavar="CITY_EXPANSIONS", help="appends expansions to current expansions")
    parser.add_option("-c", "--no-cache", action="store_true", help="Do not append existing expansions", default=False)

    (options, args) = parser.parse_args()

    if not options.cities and not options.append_cities:
        sys.exit(parser.print_help())


    city_append = options.append_cities
    handle_cities(options.cities, city_out, city_append, no_cache=options.no_cache)
    handle_csv(options.cities, geo_out, no_cache=options.no_cache)
    # handle_compatibility(options.cities, compatibility_out, no_cache=options.no_cache)

if __name__ == '__main__':
    main()
