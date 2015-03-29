#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that creates an expansion from a list of stops

For usage write expand_stops_script.py -h
"""
from __future__ import unicode_literals
import autopath
import codecs
from copy import copy
from optparse import OptionParser
from collections import defaultdict
import sys

from alex.applications.PublicTransportInfoEN.site_preprocessing import expand
from os.path import isfile

def file_check(filename, message="reading file"):
    if not filename:
        print "WARNING: " + message + " - No file specified!"
        return False
    if not isfile(filename):
        print "WARNING: " + filename + " is not a valid path!"
        return False
    return True


def get_column_index(header, caption, default):
    for i, h in enumerate(header.split(',')):
        if h == caption:
            return i
    return default


def hack_stops(stops):
    extras = set()
    for stop in stops:
        # make 'hundred'/'one hundred' variants
        if "hundred" in stop:
            extras.add(stop.replace("hundred", "one hundred"))
        # apostrophe is mandatory
        if "'s" in stop:
            extras.add(stop.replace("'s", "s"))
    stops.update(extras)


def preprocess_line(line):
    line = line.strip().title()
    line = line.replace(" Th ", "Th ")
    return line


def expand_place(stop_list):
    stops = defaultdict(list)

    for stop in stop_list:
        reverse = True
        conjunctions = [' and ', ' on ', ' at ', ]

        if '-' in stop:
            elements = stop.split('-')
        elif '(' in stop:
            elements = stop.replace(')', '').split('(')
            reverse = False
            # lexington av/63 street
        elif '/' in stop:
            elements = stop.split('/')
            # cathedral pkwy (110 st)
        elif '&' in stop:
            elements = stop.split('&')
            # BARUCH INFORMATION & TECH BLDG
        else:
            elements = [stop, ]

        expansion = [expand(el) for el in elements if len(el) > 0]

        stops[stop] = set([" ".join(expansion), " ".join(expansion[::-1]), ])
        if len(expansion) > 1:
            for conjunction in conjunctions:
                stops[stop].add(conjunction.join(expansion))
                if reverse:
                    stops[stop].add(conjunction.join(expansion[::-1]))

        hack_stops(stops[stop])
        stops[stop] = list(stops[stop])
    return stops


def load_list(filename, skip_comments=True):
    data = []
    if not file_check(filename, "loading list from file"):
        return data
    with codecs.open(filename, 'r', 'UTF-8') as fh_in:
        for line in fh_in:
            line = preprocess_line(line)
            # handle comments (strip or skip)
            if line.startswith('#'):
                if skip_comments:
                    continue
                else:
                    line = line.lstrip('#')
            data.append(line)
    return data


def read_expansions(stops_expanded_file):
    raw = read_two_columns(stops_expanded_file)
    data = {}
    for key in raw:
        data[key] = raw[key].lower().split('; ')
    return data


def read_first_column(filename, surpress_warning=True):
    data = []
    if not file_check(filename, "reading first column"):
        return data
    with codecs.open(filename, 'r', 'UTF-8') as fh_in:
        for line in fh_in:
            line = preprocess_line(line)
            # handle comments (strip or skip)
            if line.startswith('#'):
                continue

            value = line.split('\t')[0]
            if value in data and not surpress_warning:
                print "WARNING: " + value + " already appeared while reading first column from file " + filename
            data.append(value)
    return data


def read_two_columns(filename):
    data = {}
    if not file_check(filename, "reading two columns"):
        return data
    with codecs.open(filename, 'r', 'UTF-8') as stops_precedent:
        for line in stops_precedent:
            line = preprocess_line(line)

            if line.startswith('#'):
                continue
            key = line.split('\t')[0]
            data[key] = line.split('\t')[1]
    return data


def read_compatibility(filename):
    data = []
    if not file_check(filename, "reading previous compatibility"):
        return data
    with codecs.open(filename, 'r', 'UTF-8') as stops_precedent:
        for line in stops_precedent:
            line = preprocess_line(line)

            if line.startswith('#'):
                continue
            data.append(line.split('\t')[0] + '\t' + line.split('\t')[1])
    return data


def read_exports(filename):
    data = {}
    if not file_check(filename, "reading previous exports"):
        return data
    with codecs.open(filename, 'r', 'UTF-8') as exports_precedent:
        for line in exports_precedent:
            line = preprocess_line(line)

            if line.startswith('#'):
                continue
            site, sub_site, rest = line.split('\t', 2)
            key = site + '\t' + sub_site
            data[key] = rest
    return data


def merge(primary, secondary, surpress_warning=True):
    merged = copy(primary)
    for key in secondary:
        if key in primary:
            if not surpress_warning:
                print "WARNING: previous instance already contains key " + key + " while merging"
            continue
        merged[key] = secondary[key]

    return merged


def append(major, minor):
    for key in minor:
        if not key in major:
            major[key] = minor[key]
        major[key].extend(minor[key])
        major[key] = set(major[key])
    return major


def process_places(places_in, place_out, places_add, no_cache=False):
    # currently expanded places
    if no_cache:
        prev = {}
    else:
        prev = read_expansions(place_out)
    # manually added expansions of specific places not covered by automatic expansion
    manual_expansions = {} if places_add is None else read_expansions(places_add)
    # new expanded places
    expanded = expand_place(read_first_column(places_in))
    # merged new and old expansions, old ones have greater priority (no appending)
    merged = merge(prev, expanded)
    # add manual expansions to automatic ones
    append(merged, manual_expansions)
    # save it all
    save_out(place_out, merged)


def save_out(output_file, output_dict, separator="; "):
    with codecs.open(output_file, 'w', 'UTF-8') as fh_out:
        for key in sorted(output_dict):
            print >> fh_out, key + "\t" + separator.join(output_dict[key])


def save_list(output_file, output_list):
    with codecs.open(output_file, 'w', 'UTF-8') as fh_out:
        for value in sorted(output_list):
            print >> fh_out, value


def handle_csv(csv_in, csv_out, no_cache=False):
    # current data
    if no_cache:
        csv_old = {}
    else:
        csv_old = read_exports(csv_out)
    # new data
    csv_new = read_exports(csv_in)
    merged = merge(csv_old, csv_new)
    save_out(csv_out, merged, separator="")


def handle_compatibility(file_in, file_out, no_cache=False):
    # current data
    if no_cache:
        comp_old = []
    else:
        comp_old = read_compatibility(file_out)
    # new data
    comp_new = read_compatibility(file_in)
    merged = set(comp_old + comp_new)
    save_list(file_out, merged)


def main():
    stops_out = "./stops.expanded.txt"
    csv_out = "./stops.locations.csv"
    # compatibility_out = "./city.stop.txt"

    parser = OptionParser()
    parser.add_option("--stops", metavar="STOP_FILE", help="read input stops from STOP_FILE")
    parser.add_option("--append-stops", metavar="STOP_EXPANSIONS", help="appends expansions to current expansions")
    parser.add_option("-c", "--no-cache", action="store_true", help="Do not append existing expansions", default=False)

    (options, args) = parser.parse_args()

    if not options.append_stops and not options.stops:
        sys.exit(parser.print_help())

    stops_append = options.append_stops
    process_places(options.stops, stops_out, stops_append, no_cache=options.no_cache)
    handle_csv(options.stops, csv_out, no_cache=options.no_cache)
    # handle_compatibility(options.stops, compatibility_out, no_cache=options.no_cache)


if __name__ == '__main__':
    main()
