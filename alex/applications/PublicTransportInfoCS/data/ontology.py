#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from database import database
import codecs
import os
from alex.utils.config import online_update, to_project_path

# tab-separated file containing city + stop in that city, one per line
CITIES_STOPS_FNAME = 'cities_stops.tsv'
# tab-separated file containing city + all locations of the city/cities with this name
# (as pipe-separated longitude, latitude, district, region)
CITIES_LOCATION_FNAME = 'cities_locations.tsv'

# load new versions of the data files from the server
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), CITIES_STOPS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), CITIES_LOCATION_FNAME)))

ontology = {
    'slots': {
        'silence': set([]),
        'ludait': set([]),
        'task': set(['find_connection', 'find_platform', 'weather']),
        'from_stop': set(['Zličín', 'Anděl', ]),
        'to_stop': set(['Zličín', 'Anděl', ]),
        'via_stop': set(['Zličín', 'Anděl', ]),
        'from_city': set([]),
        'to_city': set([]),
        'via_city': set([]),
        'in_city': set([]),
        'departure_time': set([]),
        'departure_time_rel': set([]),
        'arrival_time': set([]),
        'arrival_time_rel': set([]),
        'time': set([]),
        'time_rel': set([]),
        'duration': set([]),
        'ampm': set(['morning', 'am', 'pm', 'evening', 'night']),
        'date': set([]),
        'date_rel': set(['today', 'tomorrow', 'day_after_tomorrow', ]),
        'centre_direction': set(['dontcare', 'dontknow', 'to', 'from', '*', ]),
        'num_transfers': set([]),
        'vehicle': set(["bus", "tram", "metro", "train", "cable_car", "ferry", ]),
        'alternative': set(['dontcare', '1', '2', '3', '4', 'last', 'next', 'prev', ]),
    },

    'slot_attributes': {
        'silence': [],
        'silence_time': [],
        'ludait': [],
        'task': [
            'user_informs',
            #'user_requests', 'user_confirms',
            #'system_informs', 'system_requests', 'system_confirms',
            #'system_iconfirms', 'system_selects',
        ],
        'from_stop': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'to_stop': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'via_stop': [
            'user_informs', 'user_requests', 'user_confirms',
            #'system_informs', 'system_requests',
            'system_confirms', 'system_iconfirms',
            #'system_selects',
        ],
        'from_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'to_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'via_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'in_city': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'departure_time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],

        'departure_time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'arrival_time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],
        'arrival_time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],
        'time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'duration': [
            'user_requests',
            'relative_time',
        ],
        'ampm': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms',
            'system_selects',
        ],
        # not implemented yet
        'date': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
        ],

        'date_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
        ],
        'centre_direction': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'num_transfers': [
            'user_requests',
            'system_informs',
        ],
        'vehicle': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
        ],
        'alternative': [
            'user_informs',
            'system_informs',
            #'system_requests',
            'system_confirms',
            #'system_iconfirms',
            #'system_selects',
        ],
        'current_time': [
            'system_informs',
            'absolute_time',
        ],
        'route_alternative': [
            # this is necessary to be defined as it is a state variable used by the policy and automatically added to
            # the dialogue state
        ],

        'lta_task': [],
        'lta_time': [],
        'lta_date': [],
        'lta_departure_time': [],
        'lta_arrival_time': [],

        # not implemented yet
        'transfer_stops': [
            'user_requests',
        ],
        'temperature': [
            'temperature',
        ],
        'min_temperature': [
            'temperature_int',
        ],
        'max_temperature': [
            'temperature',
        ],
    },
    'reset_on_change': {
        # reset slots when any of the specified slots has changed, for matching changed slots a regexp is used
        'route_alternative': [
            '^from_stop$', '^to_stop$', '^via_stop$',
            '^departure_time$', '^departure_time_rel$',
            '^arrival_time$', '^arrival_time_rel$',
            '^to_city$', '^from_city$', '^via_city$',
        ],
#        'from_stop': ['^from_city$'],
#        'to_stop': ['^to_city$'],
#        'via_stop': ['^via_city$'],
    },
    'last_talked_about': {
        # introduces new slots as a marginalisation of different inputs
        # this is performed by converting dialogue acts into inform acts
        'lta_time': {
            # the following means, every time I talk about the time, it supports the value time in slot time_sel
            'time': [('^(inform|confirm|request|select)$', '^time$', ''), ],
            # the following means, every time I talk about the time_rel, it supports the value time_rel in slot time_sel
            'time_rel': [('', '^time_rel$', ''), ],
            # as a consequence, the last slot the user talked about will have the highest probability in the ``time_sel``
            # slot
            'date_rel': [('', '^date_rel$', '')],
        },
        'lta_date': {
            'date': [('', '^date$', ''), ],
            'date_rel': [('', '^date_rel$', ''), ],
        },
        'lta_departure_time': {
            'departure_time': [('', '^departure_time$', ''), ],
            'departure_time_rel': [('', '^departure_time_rel$', ''), ],
            'time': [('^(inform|confirm|request|select)$', '^time$', ''), ],
            'time_rel': [('', '^time_rel$', ''), ],
            'date_rel': [('', '^date_rel$', '')],
        },
        'lta_arrival_time': {
            'arrival_time': [('', '^arrival_time$', ''), ],
            'arrival_time_rel': [('', '^arrival_time_rel$', ''), ],
            'date_rel': [('', '^date_rel$', '')],
        },
        'lta_task': {
            'weather': [('', '^task$', '^weather$'), ],
            'find_connection': [('', '^task$', '^find_connection$'), ('', '^departure_', ''), ('', '^arrival_', ''),
                                ('', '^from_stop$', ''), ('', '^to_stop$', ''),
                                ('', '^duration$', '')],
        },
    },

    'compatibility': {
        'stop_city': [
            'from_stop', 'to_stop', 'via_stop',
        ],
        'city_stop': [
            'from_city', 'to_city', 'via_city', 'in_city',
        ],
    },
    'compatible_values': {
        'stop_city': {},
        'city_stop': {},
    },

    'default_values': {
        'in_city': 'Praha',
    },

    'addinfo': {
        'city': {},
    },

    # translation of the values for TTS output
    'value_translation': {
        'ampm': {
            'morning': 'ráno',
            'am': 'dopoledne',
            'pm': 'odpoledne',
            'evening': 'večer',
            'night': 'v noci'
        },
        'vehicle': {
            'bus': 'autobusem',
            'intercity_bus': 'dálkovým autobusem',
            'tram': 'tramvají',
            'subway': 'metrem',
            'train': 'vlakem',
            'cable_car': 'lanovkou',
            'ferry': 'přívozem',
            'trolleybus': 'trolejbusem',
        },
        'date_rel': {
            'today': 'dnes',
            'tomorrow': 'zítra',
            'day_after_tomorrow': 'pozítří'
        },
        'alternative': {
            'dontcare': 'libovolný',
            '1': 'první',
            '2': 'druhý',
            '3': 'třetí',
            '4': 'čtvrtý',
            'last': 'poslední',
            'next': 'předchozí',
            'prev': 'následující',
        }
    },
}


def add_slot_values_from_database(slot, category, exceptions=set()):
    for value in database.get(category, tuple()):
        if value not in exceptions:
            ontology['slots'][slot].add(value)

add_slot_values_from_database('from_stop', 'stop')
add_slot_values_from_database('to_stop', 'stop')
add_slot_values_from_database('via_stop', 'stop')
add_slot_values_from_database('from_city', 'city')
add_slot_values_from_database('to_city', 'city')
add_slot_values_from_database('via_city', 'city')
add_slot_values_from_database('in_city', 'city')
add_slot_values_from_database('departure_time', 'time', exceptions=set(['now']))
add_slot_values_from_database('departure_time_rel', 'time')
add_slot_values_from_database('arrival_time', 'time', exceptions=set(['now']))
add_slot_values_from_database('arrival_time_rel', 'time')
add_slot_values_from_database('time', 'time', exceptions=set(['now']))
add_slot_values_from_database('time_rel', 'time')
add_slot_values_from_database('date_rel', 'date_rel')


def load_compatible_values(fname, slot1, slot2):
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            val_slot1, val_slot2 = line.strip().split('\t')
            # add to list of compatible values in both directions
            subset = ontology['compatible_values'][slot1 + '_' + slot2].get(val_slot1, set())
            ontology['compatible_values'][slot1 + '_' + slot2][val_slot1] = subset
            subset.add(val_slot2)
            subset = ontology['compatible_values'][slot2 + '_' + slot1].get(val_slot2, set())
            ontology['compatible_values'][slot2 + '_' + slot1][val_slot2] = subset
            subset.add(val_slot1)


dirname = os.path.dirname(os.path.abspath(__file__))
load_compatible_values(os.path.join(dirname, CITIES_STOPS_FNAME), 'city', 'stop')


def load_additional_information(fname, slot, keys):
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#') or not '\t' in line:
                continue
            data = line.strip().split('\t')
            value, data = data[0], data[1:]
            ontology['addinfo'][slot][value] = []
            for data_point in data:
                ontology['addinfo'][slot][value].append({add_key: add_val for add_key, add_val
                                                         in zip(keys, data_point.split('|'))})

load_additional_information(os.path.join(dirname, CITIES_LOCATION_FNAME), 'city', ['lon', 'lat', 'district', 'region'])
