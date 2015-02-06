#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A script that creates an expansion from a preprocessed list of states

For usage write expand_states_script.py -h
"""

from __future__ import unicode_literals
import sys
import autopath
from optparse import OptionParser
from expand_cities_script import all_to_lower
from alex.applications.PublicTransportInfoEN.data.expand_stops_script import read_expansions, read_first_column, merge, \
    append, save_out


def handle_states(states_in, states_out, states_append, no_cache=False):
    # currently expanded states
    if no_cache:
        prev = {}
    else:
        prev = read_expansions(states_out)
    # manually added expansions of specific states not covered by automatic expansion
    manual_expansions = {} if states_append is None else read_expansions(states_append)
    # new expanded states
    expanded = all_to_lower(read_first_column(states_in))
    # merged new and old expansions, old ones have greater priority (no appending)
    merged = merge(prev, expanded)
    # add manual expansions to automatic ones
    append(merged, manual_expansions)
    # save it all
    save_out(states_out, merged)


def main():
    state_out = "./states.expanded.txt"
    
    parser = OptionParser()
    parser.add_option("--states", metavar="STATE_FILE", help="read input states from STATE_FILE")
    parser.add_option("--append-states", metavar="STATE_EXPANSIONS", help="appends expansions to current expansions")
    parser.add_option("-c", "--no-cache", action="store_true", help="Do not append existing expansions", default=False)

    (options, args) = parser.parse_args()

    if not options.states and not options.append_states:
        sys.exit(parser.print_help())

    handle_states(options.states, state_out, options.append_states, no_cache=options.no_cache)

if __name__ == '__main__':
    main()
