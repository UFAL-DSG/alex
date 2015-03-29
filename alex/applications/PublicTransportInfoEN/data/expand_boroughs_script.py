#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that creates an expansion from a preprocessed list of boroughs

For usage write expand_boroughs_script.py -h
"""

from __future__ import unicode_literals
from optparse import OptionParser
from collections import defaultdict
import autopath
import sys

from alex.applications.PublicTransportInfoEN.data.expand_stops_script import read_expansions, read_first_column, \
    merge, append, save_out


def all_to_lower(site_list):
    sites = defaultdict(list)

    for site in site_list:
        sites[site] = [site.lower(),]
    return sites


def handle_boroughs(boroughs_in, boroughs_out, boroughs_append, no_cache=False):
    # currently expanded boroughs
    if no_cache:
        prev = {}
    else:
        prev = read_expansions(boroughs_out)
    # manually added expansions of specific boroughs not covered by automatic expansion
    manual_expansions = {} if boroughs_append is None else read_expansions(boroughs_append)
    # new expanded boroughs
    expanded = all_to_lower(read_first_column(boroughs_in))
    # merged new and old expansions, old ones have greater priority (no appending)
    merged = merge(prev, expanded)
    # add manual expansions to automatic ones
    append(merged, manual_expansions)
    # save it all
    save_out(boroughs_out, merged)


def main():
    borough_out = "./boroughs.expanded.txt"
    geo_out = "./boroughs.locations.csv"
    # compatibility_out = "./state.borough.txt"
    
    parser = OptionParser()
    parser.add_option("--boroughs", metavar="BOROUGH_FILE", help="read input boroughs from BOROUGH_FILE")
    parser.add_option("--append-boroughs", metavar="BOROUGH_EXPANSIONS", help="appends expansions to current expansions")
    parser.add_option("-c", "--no-cache", action="store_true", help="Do not append existing expansions", default=False)

    (options, args) = parser.parse_args()

    if not options.boroughs and not options.append_boroughs:
        sys.exit(parser.print_help())


    borough_append = options.append_boroughs
    handle_boroughs(options.boroughs, borough_out, borough_append, no_cache=options.no_cache)
    # handle_csv(options.boroughs, geo_out, no_cache=options.no_cache)
    # handle_compatibility(options.boroughs, compatibility_out, no_cache=options.no_cache)

if __name__ == '__main__':
    main()
