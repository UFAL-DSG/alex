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

        index = get_column_index(header, "stop_name", 2)

        for line in stopsFile:
            if line.startswith('#') or not line:  # skip comments and empty lines
                continue
            stop = line.split(',')[index].strip('"')
            stops.append(stop)

    return stops



def main():
    #list of tuples (label, path_to_list_of_stops)
    ls_files = [('New York', "/home/m2rtin/Desktop/transport/metro_stops.txt"),
               ('New York', '/home/m2rtin/Desktop/transport/bus_manhatten.txt'),
               ('New York', "/home/m2rtin/Desktop/transport/amtrak_20140723.txt"),
               ('Jersey City', "/home/m2rtin/Desktop/transport/njtransit_bus.txt"),
               ]

    file_out = "/home/m2rtin/alex/alex/applications/PublicTransportInfoEN/data/_expanded_stop_cities.txt"

    with codecs.open(file_out, 'w', 'UTF-8') as output:
        for (label, file) in ls_files:
            listed_stops = extract_stops(file)
            for stop in listed_stops:
                print >> output, label + "\t" + stop





if __name__ == '__main__':
    main()