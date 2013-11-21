#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
ontology = {
    'slots': {
        'silence': set([]),
        'task': set(['find_connection', 'find_platform', 'weather']),
        'from_stop': set(['Zličín', 'Anděl', ]),
        'to_stop': set(['Zličín', 'Anděl', ]),
        'via_stop': set(['Zličín', 'Anděl', ]),
        'departure_time': set(['now', '7:00', ]),
        'departure_time_rel': set(['00:05']),
        'arrival_time': set([]),
        'arrvial_time_rel': set(['00:05']),
        'duration': set([]),
        'ampm': set(['morning', 'am', 'pm', 'evening', 'night']),
        'departure_date': set([]),
        'departure_date_rel': set(['today', 'tomorrow', 'day_after_tomorrow', ]),
        'centre_direction': set(['dontcare', 'dontknow', 'to', 'from', '*', ]),
        'num_transfers': set([]),
        'vehicle': set(["bus", "tram", "metro", "train", "cable_car", "ferry", ]),
        'alternative': set(['dontcare', '1', '2', '2', '4', 'last', 'next', 'prev', ]),
    },

    'slot_attributes': {
        'silence_time': [],
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
        'weather_time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],
        'weather_time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'time': [
            'user_informs',
            'absolute_time',
        ],
        'time_rel': [
            'user_informs',
            'relative_time',
        ],
        'duration': [
            'user_requests',
            'relative_time',
        ],
        'ampm': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
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
            'system_informs',
            'user_informs',
        ],
        'current_time': [
            'system_informs',
            'absolute_time',
        ],
        'route_alternative': [
            # this is necessary to be defined as it is a state variable used by the policy and automatically added to
            # the dialogue state
        ],

        'lta_departure_time': [],
        'lta_time': [],

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
        ],
        'task': [
            '^from_stop$', '^to_stop$', '^via_stop$',
            '^departure_time$', '^departure_time_rel$',
            '^arrival_time$', '^arrival_time_rel$',
        ],
    },
    'last_talked_about': {
        # introduces new slots as a marginalisation different inputs
        # this is performed by converting dialogue acts into inform acts
        'lta_time': {
            # the following means, every time I talk about the time, it supports the value time in slot time_sel
           'time': [('.*','^time$','.*'),],
            # the following means, every time I talk about the time_rel, it supports the value time_rel in slot time_sel
           'time_rel': [('.*','^time_rel$','.*'),],
           # as a consequence, the last slot the user talked about will have the highest probability in the ``time_sel``
           # slot
        },
        'lta_departure_time': {
           'departure_time': [('.*','^departure_time$','.*'),],
           'departure_time_rel': [('.*','^departure_time_rel$','.*'),],
        },
    },
}

from database import database


def add_slot_values_from_database(slot, category):
    for value in database.get(category, tuple()):
        ontology['slots'][slot].add(value)

add_slot_values_from_database('from_stop', 'stop')
add_slot_values_from_database('to_stop', 'stop')
add_slot_values_from_database('via_stop', 'stop')
add_slot_values_from_database('departure_time', 'time')
add_slot_values_from_database('departure_time_rel', 'time_rel')
add_slot_values_from_database('arrival_time', 'time')
add_slot_values_from_database('arrival_time_rel', 'time_rel')
add_slot_values_from_database('departure_date_rel', 'date_rel')
