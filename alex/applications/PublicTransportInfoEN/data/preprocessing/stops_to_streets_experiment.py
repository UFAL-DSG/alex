#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that takes mta stops, it splits them by special characters and each item takes for a street

"""

from __future__ import unicode_literals
import codecs
import os


def get_column_index(header, caption, default):
    for i, h in enumerate(header.split(',')):
        if h.strip() == caption:
            return i
    return default


def load_list(filename):
    lines = []
    with codecs.open(filename, 'r', 'UTF-8') as fh_in:
        for line in fh_in:
            line = line.strip()
            # handle comments (strip or skip)
            if line.startswith('#'):
                continue
            lines.append(line)
    return lines


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


def extract_stops(lines):
    data = ["#stop\tcity\tlongitude|latitude"]

    for line in lines:
        if not line:
            continue
        if line.startswith('#'):
            continue
        stop, main_city, _ = line.split("\t", 2)

        if '-' in stop:
            streets = stop.split('-')
        elif '(' in stop:
            streets = stop.replace(')', '').split('(')
        elif '/' in stop:
            streets = stop.split('/')
        elif '&' in stop:
            streets = stop.split('&')
        else:
            continue

        data.extend([street + '\t' + main_city + "\tNan|Nan" for street in streets])
    return data

def write_data(file_name, data):
    with codecs.open(file_name, "w", 'UTF-8') as fh_out:
        for line in remove_duplicities(data):
            print >> fh_out, line


def main():
    file_out = "./streets_experiment.csv"
    main_city = "New York"

    # initialization
    file_stops = "/home/m2rtin/alex/alex/applications/PublicTransportInfoEN/data/stops.locations.csv"

    # load list of stops
    lines = load_list(file_stops)
    data = extract_stops(lines)
    print "writing to " + os.path.abspath(file_out)
    write_data(file_out, data)

if __name__ == '__main__':
    main()