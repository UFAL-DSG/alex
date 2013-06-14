#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

ontology = {
    'slots': {
        'from_stop': set(['Zličín', 'Anděl', ]), 
        'to_stop': set(['Zličín', 'Anděl', ]), 
        'time': set(['now', '7:00', ]), 
        'from_centre': set(['dontcare', 'dontknow', 'true', 'false']), 
        'to_centre': set(['dontcare', 'dontknow', 'true', 'false']), 
    },
        
    'slot_attributes': {
        'from_stop': [
            'user_informs','user_requests','user_confirms',
            'system_informs','system_requests','system_confirms','system_iconfirms','system_selects'
        ],
        'to_stop': [
            'user_informs','user_requests','user_confirms',
            'system_informs','system_requests','system_confirms','system_iconfirms','system_selects'
        ],
        'time': [
            'user_informs','user_requests','user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms','system_iconfirms','system_selects'
        ],
            
        'from_centre': [
            'user_informs','user_requests','user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms','system_iconfirms','system_selects'
        ],
        'to_centre': [
            'user_informs','user_requests','user_confirms',
            'system_informs',
            #'system_requests',
            'system_confirms','system_iconfirms','system_selects'
        ],
        'num_transfers': [
            'user_requests',
        ],
            
        # not implemented yet
        'transfer_stops': [
            'user_requests',
        ],
        'connection_duration': [
            'user_requests',
        ],
        'connection_price': [
            'user_requests',
        ],

        'connection_time': [
            'user_requests',
        ],

        'route_alternative': [
        ], 
    },
}

import database

def add_slot_values_from_database(slot, category):
    for value in database.database[category]:
        ontology['slots'][slot].add(value)

add_slot_values_from_database('from_stop', 'stop')
add_slot_values_from_database('to_stop', 'stop')
add_slot_values_from_database('time', 'time')

