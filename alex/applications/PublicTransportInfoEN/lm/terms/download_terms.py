#!/usr/bin/env python
# encoding: utf-8

if __name__ == '__main__':
    import autopath
    from alex.utils.config import online_update

    # terms
    online_update('applications/PublicTransportInfoEN/lm/terms/boroughs.txt')
    online_update('applications/PublicTransportInfoEN/lm/terms/cities.txt')
    online_update('applications/PublicTransportInfoEN/lm/terms/states.txt')
    online_update('applications/PublicTransportInfoEN/lm/terms/stops.txt')
    online_update('applications/PublicTransportInfoEN/lm/terms/streets.txt')
