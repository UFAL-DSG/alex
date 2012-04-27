from functools
import multiprocessing

def local_lock():
  """This decorator makes the decorated function thread safe.
   
  For each function it creates unique lock.
  """
  lock = multiprocessing.Lock()
  
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
  def decorating_function(f):
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


if __name__ == "__main__":
  class test1:
    var = 0
  
    @local_lock     
    def inc_var(self):
      X.var += 1    
      return X.var
      
  class test2:
    lock = multiprocessing.Lock()
    var = 0
    
    @global_lock(lock)
    def inc_var_1(self):
      self.var += 1    
      return X.var
    
    @global_lock(lock)
    def inc_var_2(self):
      self.var += 2    
      return self.var
  
      