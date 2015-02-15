#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == "__main__":
    import autopath

import unittest

import alex.utils.analytics as analytics

class TestAnalytics(unittest.TestCase):
    def test_analytics(self):
        a = analytics.Analytics('UA-59769647-1', 'm2rtin-ptien.com')
        a.start_session(-1)
        a.track_event('vhub', 'incomming_call')
        a.track_event('vhub', 'call_confirmed')
        a.track_event('vhub', 'call_disconected')

if __name__ == '__main__':
    unittest.main()
