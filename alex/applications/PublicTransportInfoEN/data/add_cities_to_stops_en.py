#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs


#manually adds New York in front of every stop

def get_column_index(header, caption, default):
    for i,h in enumerate(header.split(',')):
        if h == caption:
            return i
    return default


def extract_stops(file_name):

    stops = []

    with codecs.open(file_name, 'r', 'UTF-8') as stopsFile:
        header = stopsFile.readline()

        stop_index = get_column_index(header, "stop_name", 2)

        for line in stopsFile:
            if line.startswith('#') or not line:  # skip comments and empty lines
                continue
            fields = line.split(',')
            stop = fields[stop_index].strip('"')
            stops.append(stop)

    return stops



def main():
    #list of tuples (label, path_to_list_of_stops)
    ls_files = [('Staten Island', "/home/m2rtin/Desktop/transport/stops/done/bus_staten_island.txt"),
               ('New York', '/home/m2rtin/Desktop/transport/stops/done/bus_bronx.txt'),
               ('New York', '/home/m2rtin/Desktop/transport/stops/done/bus_brooklyn.txt'),
               ('New York', '/home/m2rtin/Desktop/transport/stops/done/bus_company.txt'),
               ('New York', '/home/m2rtin/Desktop/transport/stops/done/bus_manhattan.txt'),
               ('New York', '/home/m2rtin/Desktop/transport/stops/done/bus_queens.txt'),
               ('New York', '/home/m2rtin/Desktop/transport/stops/done/ferry_ny_waterway.txt'),
               ('Staten Island', '/home/m2rtin/Desktop/transport/stops/done/ferry_staten_island.txt'),
               ('New York', '/home/m2rtin/Desktop/transport/stops/done/metro_stops.txt'),
               ('New York', '/home/m2rtin/Desktop/transport/attractions.txt'),
               # ('Bronx', '/home/m2rtin/Desktop/transport/bus_bronx.txt'),
               # ('Brooklyn', '/home/m2rtin/Desktop/transport/bus_brooklyn.txt'),
               ]

    file_out = "/home/m2rtin/alex/alex/applications/PublicTransportInfoEN/data/_expanded_stop_cities.txt"

    with codecs.open(file_out, 'w', 'UTF-8') as output:
        for (label, file) in ls_files:
            listed_stops = extract_stops(file)
            for stop in listed_stops:
                print >> output, label + "\t" + stop



if __name__ == '__main__':
    main()