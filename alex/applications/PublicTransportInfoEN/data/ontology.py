#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from database import database
import codecs
import os
from alex.utils.config import online_update, to_project_path

# tab-separated file containing street + city + lon|lat coordinates + slot_specification
STREETS_TYPES_FNAME = 'streets.types.csv'
# tab-separated file containing stop + city + lon|lat coordinates
GENERAL_STOPS_LOCATIONS_FNAME = 'stops.locations.csv'
BOROUGH_STOPS_LOCATIONS_FNAME = 'stops.borough.locations.csv'
# tab-separated file containing city + state + lon|lat coordinates
CITIES_LOCATIONS_FNAME = 'cities.locations.csv'

# load new versions of the data files from the server
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), STREETS_TYPES_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), GENERAL_STOPS_LOCATIONS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), BOROUGH_STOPS_LOCATIONS_FNAME)))
online_update(to_project_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), CITIES_LOCATIONS_FNAME)))

ontology = {
    'slots': {
        'silence': set([]),
        'ludait': set([]),
        'task': set(['find_connection', 'find_platform', 'weather']),
        'from': set([]),
        'to': set([]),
        'via': set([]),
        'in': set([]),
        'stop': set([]),
        'street': set([]),
        'from_stop': set(['Central Park', 'Wall Street', ]),
        'to_stop': set(['Central Park', 'Wall Street', ]),
        'via_stop': set(['Central Park', 'Wall Street', ]),
        'from_street': set(),
        'from_street2': set(),
        'to_street': set(),
        'to_street2': set(),
        'city': set([]),
        'from_city': set([]),
        'to_city': set([]),
        'via_city': set([]),
        'in_city': set([]),
        'from_borough': set([]),
        'to_borough': set([]),
        'in_borough': set([]),
        'borough': set([]),
        'in_state': set([]),
        'state': set([]),
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
        'distance': set([]),
        'num_stops': set([]),
        'num_transfers': set([]),
        'time_transfers': set([]),
        'time_transfers_stop': set([]),
        'time_transfers_limit': set([]),
        'vehicle': set(["dontcare", "bus", "tram", "subway", "train", "cable_car", "ferry", "monorail"]),
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
        'from': [
            'user_informs',
        ],
        'to': [
            'user_informs',
        ],
        'via': [
            'user_informs',
        ],
        'in': [
            'user_informs',
        ],
        'stop': [
            'user_informs',
        ],
        'street': [
            'user_informs',
        ],
        'city': [
            'user_informs',
        ],
        'borough': [
            'user_informs',
        ],
        'state': [
            'user_informs',
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
        'from_street': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'from_street2': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'to_street': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'to_street2': [
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
        'from_borough': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'to_borough': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'in_borough': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_confirms', 'system_iconfirms',
        ],
        'in_state': [
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
        'distance': [
            'user_requests',
        ],
        'num_stops': [
            'system_informs',
        ],
        'num_transfers': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
        'time_transfers': [
            'user_requests',
        ],
        'time_transfers_stop': [
            'system_informs',
        ],
        'time_transfers_limit': [
            'system_informs',
            'relative_time',
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
        'time_zone': [
            'system_informs',
            'absolute_time',
        ],

        'lta_task': [],
        'lta_bye': [],
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

    'context_resolution': {
        # it is used DM belief tracking context that
        #   if the systems asks (request) about "from_city" and user responds (inform) "city" then it means (inform)
        #       "from_city"
        #request: set(informs)
        'street': set(['from_street', 'from_street2', 'to_street', 'to_street2', 'from_stop', 'to_stop']),
        'stop': set(['from_stop', 'to_stop', 'via_stop', 'from_street', 'from_street2', 'to_street', 'to_street2', ]),
        'city': set(['in_state', 'from_city', 'to_city', 'via_city', 'in_city', 'from_stop', 'to_stop', 'from_street', 'from_street2', 'to_street', 'to_street2', ]),
        'borough': set(['from_borough', 'to_borough', 'in_borough', 'from_city', 'to_city', 'from_stop', 'to_stop']),
        'state': set(['in_state', 'in_city']),
    },

    'reset_on_change': {
        # reset slots when any of the specified slots has changed, for matching changed slots a regexp is used
        'route_alternative': [
            '^from_stop$', '^to_stop$', '^via_stop$',
            '^departure_time$', '^departure_time_rel$',
            '^arrival_time$', '^arrival_time_rel$',
            '^to_city$', '^from_city$', '^via_city$',
            '^to_street[2]*$', '^from_street[2]*$',
            '^to_borough$', '^from_borough$',
        ],
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
        'lta_bye': {
            # if user say bye it will recorded in a separate slot. we do not have to rely on the ludait slot
            'true': [('^bye$', '', ''), ],
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

    # 'compatibility': {
    #     'city_street': ['from_street', 'from_street2', 'to_street', 'to_street2', ],
    #     'street_borough': ['in_borough', ],
    #     'stop_city': ['from_stop', 'to_stop', 'via_stop', ],
    #     'city_stop': ['from_city', 'to_city', 'via_city', 'in_city', ],
    #     'city_state': ['in_state', ],
    # },
    'compatible_values': {
        'stop_borough': {},
        'borough_stop': {},
        'street_borough': {},
        'borough_street': {},
        'street_city': {},
        'city_street': {},
        'stop_city': {},
        'city_stop': {},
        'city_state': {},
        'state_city': {},
    },

    'default_values': {
        'in_city': 'New York',
        'in_state': 'New York',
        'time_zone': 'America/New_York',
    },

    'addinfo': {
        'city': {},
        'state': {},
        'borough': {},
        'street_type': {},
    },

    # translation of the values for TTS output
    'value_translation': {
        'ampm': {
            'morning': 'morning',
            'am': 'forenoon',
            'pm': 'afternoon',
            'evening': 'evening',
            'night': 'at night'
        },
        'vehicle': {
            'dontcare': 'any means',
            'bus': 'bus',
            'intercity_bus': 'coach',
            'night_bus': 'night bus',
            'monorail': 'monorail',
            'tram': 'tram',
            'night_tram': 'night tram',
            'subway': 'subway',
            'train': 'train',
            'cable_car': 'cable car',
            'ferry': 'ferry',
            'trolleybus': 'trolley',
            'substitute_traffic': 'alternative transport',
        },
        'date_rel': {
            'today': 'today',
            'tomorrow': 'tomorrow',
            'day_after_tomorrow': 'day after tomorrow'
        },
        'alternative': {
            'dontcare': 'arbitrary',
            '1': 'first',
            '2': 'second',
            '3': 'third',
            '4': 'fourth',
            'last': 'last',
            'next': 'next',
            'prev': 'previous',
        },
        'num_transfers': {
            'dontcare': 'any number of transfers',
            '0': 'no transfers',
            '1': 'one transfer',
            '2': 'two transfers',
            '3': 'three transfers',
            '4': 'four transfers',
        },
    },
}


def add_slot_values_from_database(slot, category, exceptions=set()):
    for value in database.get(category, tuple()):
        if value not in exceptions:
            ontology['slots'][slot].add(value)

add_slot_values_from_database('street', 'street')
add_slot_values_from_database('from_street', 'street')
add_slot_values_from_database('from_street2', 'street')
add_slot_values_from_database('to_street', 'street')
add_slot_values_from_database('to_street2', 'street')
add_slot_values_from_database('stop', 'stop')
add_slot_values_from_database('from_stop', 'stop')
add_slot_values_from_database('to_stop', 'stop')
add_slot_values_from_database('via_stop', 'stop')
add_slot_values_from_database('city', 'city')
add_slot_values_from_database('from_city', 'city')
add_slot_values_from_database('to_city', 'city')
add_slot_values_from_database('via_city', 'city')
add_slot_values_from_database('in_city', 'city')
add_slot_values_from_database('borough', 'borough')
add_slot_values_from_database('from_borough', 'borough')
add_slot_values_from_database('to_borough', 'borough')
add_slot_values_from_database('in_borough', 'in_borough')
add_slot_values_from_database('state', 'state')
add_slot_values_from_database('in_state', 'state')
add_slot_values_from_database('departure_time', 'time', exceptions=set(['now']))
add_slot_values_from_database('departure_time_rel', 'time')
add_slot_values_from_database('arrival_time', 'time', exceptions=set(['now']))
add_slot_values_from_database('arrival_time_rel', 'time')
add_slot_values_from_database('time', 'time', exceptions=set(['now']))
add_slot_values_from_database('time_rel', 'time')
add_slot_values_from_database('date_rel', 'date_rel')


def load_geo_values(fname, slot1, slot2, surpress_warning=True):
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            value1, value2, geo = line.strip().split('\t')[0:3]
            value1 = value1.strip()
            value2 = value2.strip()
            geo = geo.strip()
            # expand geo coordinates
            lon, lat = geo.strip().split('|')
            if value2 not in ontology['addinfo'][slot2]:
                ontology['addinfo'][slot2][value2] = {}
            if value1 in ontology['addinfo'][slot2][value2] and not surpress_warning:
                print 'WARNING: ' + slot2 + " " + slot1 + " " + value1 + " already present!"
            ontology['addinfo'][slot2][value2][value1] = {'lon': lon, 'lat': lat}


def load_compatible_values(fname, slot1, slot2):
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            val_slot1, val_slot2 = line.strip().split('\t')[0:2]
            # add to list of compatible values in both directions
            subset = ontology['compatible_values'][slot1 + '_' + slot2].get(val_slot1, set())
            ontology['compatible_values'][slot1 + '_' + slot2][val_slot1] = subset
            subset.add(val_slot2)
            subset = ontology['compatible_values'][slot2 + '_' + slot1].get(val_slot2, set())
            ontology['compatible_values'][slot2 + '_' + slot1][val_slot2] = subset
            subset.add(val_slot1)


def load_street_type_values(fname, surpress_warning=False):  # slot1=street, slot2=borough
    # we expect to see these slots in column 'slot':  'avenue', 'street', 'place'
    with codecs.open(fname, 'r', 'UTF-8') as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            data = line.strip().split('\t')
            if len(data) < 3:
                print "ERROR: There is not enough fields to parse slot values in " + fname
                break
            val_slot1 = data[0]
            street_type = data[2].lower()
            prev_value = ontology['addinfo']['street_type'].get(val_slot1, None)
            if prev_value and prev_value != street_type and not surpress_warning:
                print 'WARNING: slot ' + val_slot1 + " already contains " + prev_value + " (overwriting with " + type + ")!"
            ontology['addinfo']['street_type'][val_slot1] = street_type


dirname = os.path.dirname(os.path.abspath(__file__))
load_street_type_values(os.path.join(dirname, STREETS_TYPES_FNAME))

load_compatible_values(os.path.join(dirname, STREETS_TYPES_FNAME), 'street', 'borough')
load_compatible_values(os.path.join(dirname, GENERAL_STOPS_LOCATIONS_FNAME), 'stop', 'city')
load_compatible_values(os.path.join(dirname, BOROUGH_STOPS_LOCATIONS_FNAME), 'stop', 'borough')
load_compatible_values(os.path.join(dirname, CITIES_LOCATIONS_FNAME), 'city', 'state')

load_geo_values(os.path.join(dirname, BOROUGH_STOPS_LOCATIONS_FNAME), 'stop', 'borough')
load_geo_values(os.path.join(dirname, GENERAL_STOPS_LOCATIONS_FNAME), 'stop', 'city')
load_geo_values(os.path.join(dirname, CITIES_LOCATIONS_FNAME), 'city', 'state')
