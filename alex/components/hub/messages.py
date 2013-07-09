#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import collections
import time

from datetime import datetime

from alex.utils.text import parse_command
from alex.utils.mproc import InstanceID

# TODO: add comments


class Message(InstanceID):
    """ Abstract class which implements basic functionality for messages passed between components in the alex.
    """
    def __init__(self, source, target):
        self.id = self.get_instance_id()
        self.time = datetime.now()
        self.source = source
        self.target = target

    def get_time_str(self):
        """ Return current time in dashed ISO-like format.
        """
        return '{dt}-{tz}'.format(dt=self.time.strftime('%Y-%m-%d-%H-%M-%S.%f'),
            tz=time.tzname[time.localtime().tm_isdst])

class Command(Message):
    def __init__(self, command, source=None, target=None):
        Message.__init__(self, source, target)

        self.command = command
        self.parsed = collections.defaultdict(unicode, parse_command(self.command))

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return "#%-6d Time: %s From: %-10s To: %-10s Command: %s " % (self.id, self.get_time_str(), self.source, self.target, self.command)

class ASRHyp(Message):
    def __init__(self, hyp, source=None, target=None, fname = None):
        Message.__init__(self, source, target)

        self.hyp = hyp
        self.fname = fname

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return "#%-6d Time: %s From: %-10s To: %-10s Hyp: %s fname: %s" % (self.id, self.get_time_str(), self.source, self.target, self.hyp, self.fname)

class SLUHyp(Message):
    def __init__(self, hyp, asr_hyp=None, source=None, target=None):
        Message.__init__(self, source, target)

        self.hyp = hyp
        self.asr_hyp = asr_hyp

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return "#%-6d Time: %s From: %-10s To: %-10s Hyp: %s " % (self.id, self.get_time_str(), self.source, self.target, self.hyp)

class DMDA(Message):
    def __init__(self, da, source=None, target=None):
        Message.__init__(self, source, target)

        self.da = da

    def __str__(self):
        return "#%-6d Time: %s From: %-10s To: %-10s Hyp: %s " % (self.id, self.get_time_str(), self.source, self.target, self.da)

class TTSText(Message):
    def __init__(self, text, source=None, target=None):
        Message.__init__(self, source, target)

        self.text = text

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
            return "#%-6d Time: %s From: %-10s To: %-10s Text: %s " % (self.id, self.get_time_str(), self.source, self.target, self.text)


class Frame(Message):
    def __init__(self, payload, source=None, target=None):
        Message.__init__(self, source, target)

        self.payload = payload

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
            return "#%-6d Time: %s From: %-10s To: %-10s Len: %d " % (self.id, self.get_time_str(), self.source, self.target, len(self.payload))

    def __len__(self):
        return len(self.payload)

    def __getitem__(self, key):
        return self.payload[key]
