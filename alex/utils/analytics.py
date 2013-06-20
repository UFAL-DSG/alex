#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyga.requests import Tracker, Page, Event, Session, Visitor

class Analytics(object):
    def __init__(self, account_id, domain_name):
        self.account_id = account_id
        self.domain_name = domain_name

    def __repr__(self):
        return "Analytics(account_id='{account_id}', domain_name='{domain_name}')".\
            format(account_id=self.account_id, domain_name=self.domain_name)

    def start_session(self, caller_id):
        self.caller_id = caller_id
        
        self.tracker = Tracker(self.account_id, self.domain_name)
        self.visitor = Visitor()
        self.visitor.user_agent = self.caller_id
        self.session = Session()
        
    def track_pageview(self, page):
        self.tracker.track_pageview(Page(page), self.session, self.visitor)        
        
    def track_event(self, category=None, action=None, label=None, value=None):
        if label is None:
            label = self.caller_id
            
        self.tracker.track_event(Event(category, action, label, value), self.session, self.visitor)        
