#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

def split_to_bins(A,  S = 4):
  """Split the A array into bins of size N."""
  m, n = divmod(len(A), S)
  return [A[i*S:(i+1)*S] for i in range(m+bool(n))]

def flatten(l, ltypes=(list, tuple)):
  """Faltten nested list into a simple list."""

  ltype = type(l)
  l = list(l)
  i = 0
  while i < len(l):
    while isinstance(l[i], ltypes):
      if not l[i]:
        l.pop(i)
        i -= 1
        break
      else:
        l[i:i + 1] = l[i]
    i += 1
  return ltype(l)

def get_text_from_xml_node(node):
    rc = []
    for cn in node.childNodes:
        if cn.nodeType == cn.TEXT_NODE:
            rc.append(cn.data)
    return ''.join(rc).strip()

class nesteddict(defaultdict):
  def __init__(self):
     defaultdict.__init__(self, nesteddict)

  def walk(self):
    for key, value in self.iteritems():
      if isinstance(value, nesteddict):
        for tup in value.walk():
          yield (key,) + tup
        else:
          yield key, value
