#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import cStringIO
import pprint
from SDS.utils.mproc import SystemLogger

class Config:
  """ Config handles configuration data necessary for all the components
  in the SDS. It implements a dictionary so that any component could
  store arbitrary structured data.

  """

  def __init__(self, file_name):
    self.config = {}

    if file_name:
      self.load(file_name)

  def __len__(self):
    return len(self.config)

  def __getitem__(self, i):
    return self.config[i]

  def __iter__(self):
    for i in self.config:
      yield i

  def __str__(self):
    sio = cStringIO.StringIO()
    pprint.pprint(self.config, sio, indent=2, width=120)
    return sio.getvalue()

  def load(self, file_name):
    """FIX: Executing external files is not ideal! It should be changed in the future!
    """
    execfile(file_name, globals())
    self.config = config

  def merge(self, file_name):
    execfile(file_name, globals())
    self.update_dict(self.config, config)

  def update_dict(self, d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = self.update_dict(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

