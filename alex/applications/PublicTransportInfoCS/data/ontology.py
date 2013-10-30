#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

ontology = {
    'slots': {
        'from_stop': set(['Zličín', 'Anděl', ]),
        'to_stop': set(['Zličín', 'Anděl', ]),
        'time': set(['now', '7:00', ]),
        'time_rel': set(['now', '7:00', ]),
        'ampm': set(['morning', 'am', 'pm', 'evening', 'night']),
        'date': set([]),
        'date_rel': set(['today', 'tomorrow', ]),
        'centre_direction': set(['dontcare', 'dontknow', 'true', 'false', ]),
        'alternative': set(['dontcare', 'first', 'second', 'third', 'forth',
                            'last', 'next', 'prev', ]),
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
        'time': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'absolute_time',
        ],

        'time_rel': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms', 'system_iconfirms', 'system_selects',
            'relative_time',
        ],
        'ampm': [
            'user_informs', 'user_requests', 'user_confirms',
            'system_informs', 'system_requests', 'system_confirms',
            'system_iconfirms', 'system_selects',
        ],
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
        'alternative': [
            'user_informs',
        ],

        'duration': [
            'relative_time',
        ],

        'departure_time': [
            'absolute_time',
        ],

        'arrival_time': [
            'absolute_time',
        ],

        # not implemented yet
        'transfer_stops': [
            'user_requests',
        ],
    },
}

from database import database


def add_slot_values_from_database(slot, category):
    for value in database.get(category, tuple()):
        ontology['slots'][slot].add(value)

add_slot_values_from_database('from_stop', 'stop')
add_slot_values_from_database('to_stop', 'stop')
add_slot_values_from_database('time', 'time')
