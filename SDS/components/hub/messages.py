#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing
import collections
import time

from SDS.utils.text import parse_command
from SDS.utils.mproc import InstanceID

# TODO: add comments


class Message(InstanceID):
    """ Abstract class which implements basic functionality for messages passed between components in the SDS.
    """
    def __init__(self, source, target):
        self.id = self.get_instance_id()
        self.time = time.time()
        self.source = source
        self.target = target


class Command(Message):
    def __init__(self, command, source=None, target=None):
        Message.__init__(self, source, target)

        self.command = command
        self.parsed = collections.defaultdict(str, parse_command(self.command))

    def __str__(self):
        return "From: %-10s To: %-10s Command: %s " % (self.source, self.target, self.command)


class ASRHyp(Message):
    def __init__(self, hyp, source=None, target=None):
        Message.__init__(self, source, target)

        self.hyp = hyp

    def __str__(self):
        return "From: %-10s To: %-10s Hyp: %s " % (self.source, self.target, self.hyp)

class SLUHyp(Message):
    def __init__(self, hyp, source=None, target=None):
        Message.__init__(self, source, target)

        self.hyp = hyp

    def __str__(self):
        return "From: %-10s To: %-10s Hyp: %s " % (self.source, self.target, self.hyp)

class DMDA(Message):
    def __init__(self, da, source=None, target=None):
        Message.__init__(self, source, target)

        self.da = da

    def __str__(self):
        return "From: %-10s To: %-10s Hyp: %s " % (self.source, self.target, self.da)

class TTSText(Message):
    def __init__(self, text, source=None, target=None):
        Message.__init__(self, source, target)

        self.text = text

    def __str__(self):
        return "From: %-10s To: %-10s Text: %s " % (self.source, self.target, self.text)


class Frame(Message):
    def __init__(self, payload, source=None, target=None):
        Message.__init__(self, source, target)

        self.payload = payload

    def __str__(self):
        return "From: %-10s To: %-10s Len: %d " % (self.source, self.target, len(self.payload))

    def __len__(self):
        return len(self.payload)

    def __getitem__(self, key):
        return self.payload[key]