#!/usr/bin/env python
# -*- coding: utf-8 -*-

import autopath

from alex.utils.config import online_update

online_update('applications/PublicTransportInfoEN/data/states.expanded.txt')
online_update('applications/PublicTransportInfoEN/data/cities.expanded.txt')
online_update('applications/PublicTransportInfoEN/data/stops.expanded.txt')

online_update('applications/PublicTransportInfoEN/data/cities.locations.csv')
online_update('applications/PublicTransportInfoEN/data/stops.locations.csv')

# online_update('applications/PublicTransportInfoEN/data/czech.dict')
# online_update('applications/PublicTransportInfoEN/data/czech.tagger')

# #online_update('applications/PublicTransportInfoEN/data/stops-idos.tsv')
# #online_update('applications/PublicTransportInfoEN/data/cities.txt')
# online_update('applications/PublicTransportInfoEN/data/stops.txt')
# online_update('applications/PublicTransportInfoEN/data/cities.expanded.txt')
# online_update('applications/PublicTransportInfoEN/data/stops.expanded.txt')
# online_update('applications/PublicTransportInfoEN/data/cities_stops.tsv')
# #online_update('applications/PublicTransportInfoEN/data/cities_locations.tsv')
# online_update('applications/PublicTransportInfoEN/data/idos_map.tsv')
