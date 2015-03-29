#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that basically creates a csv file that contains a list of places from INPUT_FILE sith second
column of a STRING_SAME_FOR_ALL and the benefit is that it can merge with already existing OUTPUT_FILE
 unless -c flag is set.

Usage:
/.compatibility_script_manual --name OUTPUT_FILE --main-place STRING_SAME_FOR_ALL --list INPUT_FILE [-c]
"""

from __future__ import unicode_literals
import codecs
from optparse import OptionParser
from alex.applications.PublicTransportInfoEN.data.expand_stops_script import read_first_column, file_check


def read_prev_compatibility(filename):
    data = set()
    if not file_check(filename, "reading previous compatibility list"):
        return data
    with codecs.open(filename, 'r', 'UTF-8') as cities_precedent:
        for line in cities_precedent:
            line = line.strip()

            if line.startswith('#'):
                    continue
            city, state = line.split('\t')[0:2]
            pair = city + '\t' + state
            if pair in data:
                print "WARNING: pair " + pair + " is already in the compatibility list!"
            data.add(pair)
    return data


def stick_place_in_front(place, list):
    data = set()
    for value in list:
        pair = place + '\t' + value
        if pair in data:
                print "WARNING: pair " + pair + " is already present while sticking a place " + place + " in front a list of places!"
        data.add(pair)
    return data


def save_set(output_file, output_set, separator="; "):
    with codecs.open(output_file, 'w', 'UTF-8') as fh_out:
        for value in sorted(output_set):
            print >> fh_out, value


def handle_compatibility(file_in, file_out, main_place, no_cache=False):
    # so far expanded list
    if no_cache:
        prev = set()
    else:
        prev = read_prev_compatibility(file_out)
    # newly expanded list
    expanded = stick_place_in_front(main_place, read_first_column(file_in))
    # merged new and old expansions, old ones have greater priority
    merged = prev | expanded
    # save it all
    save_set(file_out, merged)


def main():
    parser = OptionParser()
    parser.add_option("--name", metavar="OUTPUT_NAME", help="OUTPUT_NAME is the name of output file")
    parser.add_option("--main-place", metavar="MAIN_PLACE", help="MAIN_PLACE is a main compatible place as a string")
    parser.add_option("--list", metavar="COMPATIBLE_PLACES", help="read input places from COMPATIBLE_PLACES")
    parser.add_option("-c", "--no-cache", action="store_true", help="Do not append existing expansions", default=False)

    (options, args) = parser.parse_args()

    if options.name and options.list and options.main_place:
        handle_compatibility(options.list, "./" + options.name, options.main_place, no_cache=options.no_cache)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
