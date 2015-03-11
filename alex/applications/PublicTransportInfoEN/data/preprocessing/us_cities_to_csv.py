#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that takes us cities (city\tstate_code)file and state-codes and it joins them

Usage:

./us_cities_to_csv.py [-o: output_file] cities.txt state-codes.txt
"""

from __future__ import unicode_literals
import codecs
import os
import sys
from getopt import getopt


def get_column_index(header, caption, default):
    for i, h in enumerate(header.split('-')):
        if h == caption:
            return i
    return default


def load_list(filename, skip_comments=True):
    lines = []
    with codecs.open(filename, 'r', 'UTF-8') as fh_in:
        header = fh_in.readline()
        for line in fh_in:
            line = line.strip()
            # handle comments (strip or skip)
            if line.startswith('#'):
                if skip_comments:
                    continue
                else:
                    line = line.lstrip('#')
            lines.append(line)
    return lines, header


def load_state_code_dict(file_state_codes, skip_comments=True):
    dict = {}
    with codecs.open(file_state_codes, 'r', 'UTF-8') as fh_in:
        for line in fh_in:
            line = line.strip()
            # handle comments (strip or skip)
            if line.startswith('#'):
                if skip_comments:
                    continue
                else:
                    line = line.lstrip('#')
            state, code = line.split('\t')
            dict[code] = state
    return dict


def remove_duplicities(lines):
    data = remove_following_duplicities(sorted(lines))
    chunks = group_by_city_and_state(data)
    return [average_same_city(chunks.get(key)) for key in sorted(chunks.keys())]


def group_by_city_and_state(data):
    dict = {}
    for line in data:
        if line.startswith('#'):
            key = '#'
        else:
            city, state = line.split('\t')[0:2]
            key = city + '_' + state

        if not key in dict:
            dict[key] = []
        dict[key].append(line)

    return dict


def remove_following_duplicities(lines):
    previous = "could_not_be_possibly_a_previous_line"
    output = []
    for line in sorted(lines):
        if previous == line:
            continue
        output.append(line)
        previous = line
    return output


def average_same_city(same_stops):
    city = ""
    state = ""
    longitude_sum = float(0)
    latitude_sum = float(0)
    for line in same_stops:
        if line.startswith('#'):
            return ";".join(same_stops)  # join comments to one line
        city, state, geo = line.split('\t')
        longitude, latitude = geo.split('|')
        longitude_sum += float(longitude)
        latitude_sum += float(latitude)
    return "\t".join([city, state, str(longitude_sum/len(same_stops)) + '|' + str(latitude_sum/len(same_stops))])


def extract_fields(lines, header, state_dictionary, skip_comments=True):
    state_code_index = get_column_index(header, "state", 1)
    city_index = get_column_index(header, "city", 2)
    lat_index = get_column_index(header, "lat", 3)
    lon_index = get_column_index(header, "lng", 4)

    data = ["#city\tstate\tlongitude|latitude"]

    for line in lines:
        if not line:
            continue
        if line.startswith('#'):
            if skip_comments:
                continue
            else:
                line.lstrip('#')

        fields = line.strip().split(',')
        if len(fields) > len(header.split('-')):
            print "different lengths!"

        state_code = fields[state_code_index].strip().strip('"')
        city = fields[city_index].strip().strip('"')
        latitude = fields[lat_index].strip().strip('"')
        longitude = fields[lon_index].strip().strip('"')

        state = state_dictionary[state_code]

        data.append('\t'.join([city, state, longitude + '|' + latitude]))
    return data


def write_data(file_name, data):
    with codecs.open(file_name, "w", 'UTF-8') as fh_out:
        for line in remove_duplicities(data):
            print >> fh_out, line


def main():
    opts, files = getopt(sys.argv[1:], '-o:')
    file_out = "./us_cities_to_csv.csv"
    for opt, arg in opts:
        if opt == '-o':
            file_out = arg

    # sanity check
    if len(files) != 2:
        sys.exit(__doc__)

    # initialization
    file_stops = files[0]
    file_state_codes = files[1]

    # load list of cities
    state_dictionary = load_state_code_dict(file_state_codes)
    lines, header = load_list(file_stops)
    data = extract_fields(lines, header, state_dictionary)
    print "writing to " + os.path.abspath(file_out)
    write_data(file_out, data)

if __name__ == '__main__':
    main()