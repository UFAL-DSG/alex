#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing

from SDS.utils.string import parse_command
from SDS.utils.multiprocessing import InstanceID

# TODO: add comments

class Command(InstanceID):
  def __init__(self, command, source = None, target = None):
    self.id = self.get_instance_id()
    
    self.command = command
    self.source = source
    self.target = target
    
    self.parsed = parse_command(self.command)
    
  def __str__(self):
    return "From: %s To: %s Commamnd: %s " % (self.source, self.target, self.command)

class ASRHyp(InstanceID):
  def __init__(self, hyp, source = None, target = None):
    self.id = self.get_instance_id()

    self.hyp = hyp
    self.source = source
    self.target = target
    
  def __str__(self):
    return "From: %s To: %s Hyp: %s " % (self.source, self.target, self.hyp)

  def __len__(self):
    return len(self.payload)
    
  def __getitem__(self, key):
    return self.payload[key]
    
class TTSText(InstanceID):
  def __init__(self, text, source = None, target = None):
    self.id = self.get_instance_id()

    self.text = text
    self.source = source
    self.target = target
    
  def __str__(self):
    return "From: %s To: %s Text: %s " % (self.source, self.target, self.text)

class Frame(InstanceID):
  def __init__(self, payload, source = None, target = None):
    self.id = self.get_instance_id()
    
    self.payload = payload
    self.source = source
    self.target = target
    
  def __str__(self):
    return "From: %s To: %s Len: %d " % (self.source, target, self.len(self.payload))

  def __len__(self):
    return len(self.payload)
    
  def __getitem__(self, key):
    return self.payload[key]
