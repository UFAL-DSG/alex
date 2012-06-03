#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import threading

def local_lock():
  """This decorator makes the decorated function thread safe.
   
  For each function it creates unique lock.
  """
  lock = threading.Lock()
  
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
  lock = threading.Lock()
  instance_id = 0
  
  @global_lock(lock)
  def get_instance_id(self):
    InstanceID.instance_id += 1    
    return InstanceID.instance_id

if __name__ == "__main__":
  class test1:
    var = 0
  
    @local_lock     
    def inc_var(self):
      self.var += 1    
      return self.var
      
  class test2:
    lock = threading.Lock()
    var = 0
    
    @global_lock(lock)
    def inc_var_1(self):
      self.var += 1    
      return self.var
    
    @global_lock(lock)
    def inc_var_2(self):
      self.var += 2    
      return self.var
  
      
