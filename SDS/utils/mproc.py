#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import multiprocessing

def local_lock():
  """This decorator makes the decorated function thread safe.

  For each function it creates unique lock.
  """
  lock = multiprocessing.Lock()

  def decorator(user_function):
    @functools.wraps(user_function)
    def wraper(*args, **kw):
      lock.acquire()
      try:
        return user_function(*args, **kw)
      except Exception as e:
        raise e
      finally:
        lock.release()

    return wraper

  return decorator

def global_lock(lock):
  """This decorator makes the decorated function thread safe.

  It uses provided global lock.
  """
  def decorator(user_function):
    @functools.wraps(user_function)
    def wraper(*args, **kw):
      lock.acquire()
      try:
        return user_function(*args, **kw)
      except Exception as e:
        raise e
      finally:
        lock.release()

    return wraper

  return decorator

class InstanceID:
  lock = multiprocessing.Lock()
  instance_id = 0

  @global_lock(lock)
  def get_instance_id(self):
    InstanceID.instance_id += 1
    return InstanceID.instance_id

