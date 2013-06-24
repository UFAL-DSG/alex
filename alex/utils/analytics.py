#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import traceback

from pyga.requests import Tracker, Page, Event, Session, Visitor

from alex.utils.mproc import async


class Analytics(object):
    """
    This is a wrapper for Google Analytics tracking code.

    All interaction with GA should be asynchronous so that the main code is not
    delayed.
    """
    def __init__(self, account_id=None, domain_name=None):
        self.account_id = account_id
        self.domain_name = domain_name

    def __repr__(self):
        return ("Analytics(account_id='{account_id}', "
                "domain_name='{domain_name}')").format(
                    account_id=self.account_id, domain_name=self.domain_name)

    def start_session(self, caller_id):
        self.caller_id = caller_id

        if self.account_id:
            self.tracker = Tracker(self.account_id, self.domain_name)

            self.visitor = Visitor()
            self.visitor.user_agent = self.caller_id
            self.visitor.unique_id = hash(caller_id) & 0x7fffffff

#            print self.visitor.unique_id
#            print self.visitor.__getstate__()

            self.session = Session()

    @async
    def track_pageview(self, page):
        try:
            if self.account_id:
                self.tracker.track_pageview(Page(page), self.session,
                                            self.visitor)
        except:
            print('Uncaught exception in Analytics process:\n'
                  + traceback.format_exc())

    @async
    def track_event(self, category=None, action=None, label=None, value=None):
        try:
            if self.account_id:
                if label is None:
                    label = self.caller_id

                self.tracker.track_event(Event(category, action, label, value),
                                         self.session, self.visitor)
        except:
            print('Uncaught exception in Analytics process:\n'
                  + traceback.format_exc())
