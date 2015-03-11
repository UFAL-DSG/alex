#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that takes mta stops file and it selects important fields and saves them (works with GTFS mainly)
Usage:

./mta_to_csv.py [-m: main_city] [-o: output_file] stops.txt
"""

from __future__ import unicode_literals
import codecs
import os
import sys
from getopt import getopt


def get_column_index(header, caption, default):
    for i, h in enumerate(header.split(',')):
        if h.strip() == caption:
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


def remove_duplicities(lines):
    data = remove_following_duplicities(sorted(lines))
    chunks = group_by_name(data)
    return [average_same_stops(chunks.get(key)) for key in sorted(chunks.keys())]


def group_by_name(data):
    dict = {}
    for line in data:
        if line.startswith('#'):
            name = '#'
        else:
            name = line.split('\t')[0]

        if not name in dict:
            dict[name] = []
        dict[name].append(line)

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


def average_same_stops(same_stops):
    stop = ""
    city = ""
    longitude_sum = float(0)
    latitude_sum = float(0)
    for line in same_stops:
        if line.startswith('#'):
            return ";".join(same_stops)  # join comments to one line
        stop, city, geo = line.split('\t')
        longitude, latitude = geo.split('|')
        longitude_sum += float(longitude)
        latitude_sum += float(latitude)
    return "\t".join([stop, city, str(longitude_sum/len(same_stops)) + '|' + str(latitude_sum/len(same_stops))])


def extract_fields(lines, header, main_city, skip_comments=True):
    stop_index = get_column_index(header, "stop_name", 2)
    lat_index = get_column_index(header, "stop_lat", 4)
    lon_index = get_column_index(header, "stop_lon", 5)

    data = ["#stop\tcity\tlongitude|latitude"]

    for line in lines:
        if not line:
            continue
        if line.startswith('#'):
            if skip_comments:
                continue
            else:
                line.lstrip('#')

        fields = line.strip().split(',')
        if len(fields) > len(header.split(',')):
            split = line.split('"')
            split[1] = split[1].replace(',',';')
            fields = '"'.join(split).split(',')
        if len(fields) != len(header.split(',')):
            print "different lengths!"

        stop = fields[stop_index].strip().strip('"')
        latitude = fields[lat_index].strip().strip('"')
        longitude = fields[lon_index].strip().strip('"')

        data.append('\t'.join([stop, main_city, longitude + '|' + latitude]))
    return data

def write_data(file_name, data):
    with codecs.open(file_name, "w", 'UTF-8') as fh_out:
        for line in remove_duplicities(data):
            print >> fh_out, line


def main():
    file_out = "./mta_to_csv.csv"
    main_city = "New York"

    opts, files = getopt(sys.argv[1:], '-o:m:')
    for opt, arg in opts:
        if opt == '-o':
            file_out = arg
        if opt == '-m':
            main_city = arg


    # sanity check
    if len(files) != 1:
        sys.exit(__doc__)

    # initialization
    file_stops = files[0]

    # load list of stops
    lines, header = load_list(file_stops)
    data = extract_fields(lines, header, main_city)
    print "writing to " + os.path.abspath(file_out)
    write_data(file_out, data)

if __name__ == '__main__':
    main()
