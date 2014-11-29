#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == '__main__':
    import autopath
from alex.utils.config import online_update


if __name__ == '__main__':
    online_update('applications/PublicTransportInfoCS/data/czech.dict')
    online_update('applications/PublicTransportInfoCS/data/czech.tagger')

#online_update('applications/PublicTransportInfoCS/data/stops-idos.tsv')
#online_update('applications/PublicTransportInfoCS/data/cities.txt')
    online_update('applications/PublicTransportInfoCS/data/stops.txt')
    online_update('applications/PublicTransportInfoCS/data/cities.expanded.txt')
    online_update('applications/PublicTransportInfoCS/data/stops.expanded.txt')
    online_update('applications/PublicTransportInfoCS/data/cities_stops.tsv')
#online_update('applications/PublicTransportInfoCS/data/cities_locations.tsv')
    online_update('applications/PublicTransportInfoCS/data/idos_map.tsv')
