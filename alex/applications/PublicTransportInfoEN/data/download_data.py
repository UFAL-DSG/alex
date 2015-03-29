#!/usr/bin/env python
# -*- coding: utf-8 -*-

import autopath

from alex.utils.config import online_update

online_update('applications/PublicTransportInfoEN/data/states.expanded.txt')
online_update('applications/PublicTransportInfoEN/data/cities.expanded.txt')
online_update('applications/PublicTransportInfoEN/data/stops.expanded.txt')
online_update('applications/PublicTransportInfoEN/data/streets.expanded.txt')
online_update('applications/PublicTransportInfoEN/data/boroughs.expanded.txt')

online_update('applications/PublicTransportInfoEN/data/cities.locations.csv')
online_update('applications/PublicTransportInfoEN/data/stops.locations.csv')
online_update('applications/PublicTransportInfoEN/data/stops.borough.locations.csv')
online_update('applications/PublicTransportInfoEN/data/streets.types.csv')
