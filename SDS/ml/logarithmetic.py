#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import scipy as sp

""" This is an example module for log based arithmetic. Since there is support in numpy for such arithmetic,
the numpy should be used directly and save time for calling these functions.

Use this module to get inspiration how to perform log based arithmetic.

Especially consider using:
  numpy.logaddexp(a,b) - add to probability values in the log domain
  scipy.misc.logsumexp(a) - sum an array with values in the log domain

"""

zero_prob = -30.0
one_prob = 0.0

def linear_to_log(a):
  """Converts a vector from the linear domain to the log domain."""
  return np.log(a)

def log_to_linear(a):
  """Converts a vector from the log domain to the linear domain."""
  return np.exp(a)

def normalise(a):
  """normalises the input probability vector to sum to one in the log domain.

  This is equivalent to a/sum(a) in the linear domain.
  """
  return a - sp.misc.logsumexp(a)

def multiply(a, b):
  """Computes pairwise multiplication between vectors a and b in the log domain.

  This is equivalent to [a1*b1, a2*b2, ...] in the linear domain.
  """
  return a+b

def devide(a, b):
  """Computes pairwise division between vectors a and b in the log domain.

  This is equivalent to [a1/b1, a2/b2, ...] in the linear domain.
  """
  return a-b

def add(a, b):
  """Computes pairwise addition of two vectors in the log domain.

  This is equivalent to [a1+b1, a2+b2, ...] in the linear domain..
  """
  return np.logaddexp(a, b)

def sub(a, b):
  """Computes pairwise subtraction of two vectors in the log domain.

  This is equivalent to [a1-b1, a2-b2, ...] in the linear domain.
  """
  return np.logaddexp(a, -b)

def dot(a, b):
  """Computes dot product in the log domain.

  This is equivalent to a1*b1+a2*b2+... in the linear domain.
  """
  return sp.misc.logsumexp(a+b)

def sum(a, axis=None):
  # scipy implementation of logsumexp
  # -----------------------------------------------------------------------
  # def logsumexp(a):
  #   """Compute the log of the sum of exponentials log(e^{a_1}+...e^{a_n})
  #   of the components of the array a, avoiding numerical overflow.
  #   """
  #   a = asarray(a)
  #   a_max = a.max()
  #   return a_max + log((exp(a-a_max)).sum())

  if axis is None:
    a = np.asarray(a)
    a_max = a.max()
    return a_max + np.log((np.exp(a-a_max)).sum())

  a = np.asarray(a)
  shp = list(a.shape)
  shp[axis] = 1
  a_max = a.max(axis=axis)
  s = np.log(np.exp(np.a - a_max.reshape(shp)).sum(axis=axis))
  lse  = a_max + s
  return lse
