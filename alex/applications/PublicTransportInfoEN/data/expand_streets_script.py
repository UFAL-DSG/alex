#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that creates an expansion from a list of stops

For usage write expand_stops_script.py -h
"""

from __future__ import unicode_literals
from optparse import OptionParser
import sys
import autopath

from alex.applications.PublicTransportInfoEN.data.expand_stops_script import process_places, handle_csv


def main():
    streets_out = "./streets.expanded.txt"
    csv_out = "./streets.types.csv"
    # compatibility_out = "./city.street.txt"
    
    parser = OptionParser()
    parser.add_option("--streets", metavar="STREET_FILE", help="read input streets from STREET_FILE")
    parser.add_option("--append-streets", metavar="STREET_EXPANSIONS", help="appends expansions to current expansions")
    parser.add_option("-c", "--no-cache", action="store_true", help="Do not append existing expansions", default=False)

    (options, args) = parser.parse_args()

    if not options.append_streets and not options.streets:
        sys.exit(parser.print_help())

    streets_append = options.append_streets
    process_places(options.streets, streets_out, streets_append, no_cache=options.no_cache)
    handle_csv(options.streets, csv_out, no_cache=options.no_cache)
    # handle_compatibility(options.streets, compatibility_out, no_cache=options.no_cache)

if __name__ == '__main__':
    main()
