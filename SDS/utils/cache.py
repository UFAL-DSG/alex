#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pylint: disable-msg=E1103


import collections
import functools
import os
import os.path
import cPickle as pickle
import fcntl
import hashlib

from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter

persistent_cache_directory = '~/.SDS_persistent_cache'


class Counter(dict):
    'Mapping where default values are zero'
    def __missing__(self, key):
        return 0


def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10

    def decorator(user_function,
                  len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                  # mapping of args to results
        queue = collections.deque()  # order that keys have been used
        refcount = Counter()        # times each key is in the queue
        sentinel = object()         # marker for looping around the queue
        kwd_mark = object()         # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    del cache[key], refcount[key]

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1

            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear

        return wrapper

    return decorator


def lfu_cache(maxsize=100):
    '''Least-frequently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    '''
    def decorator(user_function):
        cache = {}                      # mapping of args to results
        use_count = Counter()           # times each key has been accessed
        kwarg_mark = object()           # separate positional and keyword args

        @functools.wraps(user_function)
        def wrapper(*args, **kwargs):
            key = args
            if kwargs:
                key += (kwarg_mark,) + tuple(sorted(kwargs.items()))

            # get cache entry or compute if not found
            try:
                result = cache[key]
                use_count[key] += 1
                wrapper.hits += 1
            except KeyError:
                # need to add something to the cache, make room if necessary
                if len(cache) == maxsize:
                    for k, _ in nsmallest(maxsize // 10 or 1,
                                          use_count.iteritems(),
                                          key=itemgetter(1)):
                        del cache[k], use_count[k]
                cache[key] = user_function(*args, **kwargs)
                result = cache[key]
                use_count[key] += 1
                wrapper.misses += 1
            return result

        def clear():
            cache.clear()
            use_count.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        wrapper.cache = cache

        return wrapper

    return decorator


def get_persitent_cache_content(key):
    key_name = persistent_cache_directory + '/' + '_'.join([str(i) for i in key]).replace(' ', '_')
    try:
        f = open(key_name, 'rb')
        fcntl.lockf(f, fcntl.LOCK_EX)
    except IOError:
        raise KeyError

    data = pickle.load(f)

    fcntl.lockf(f, fcntl.LOCK_UN)
    f.close()

    return data


def set_persitent_cache_content(key, value):
    key_name = persistent_cache_directory + '/' + '_'.join([str(i) for i in key]).replace(' ', '_')
    f = open(key_name, 'wb')
    fcntl.lockf(f, fcntl.LOCK_EX)

    data = pickle.dump(value, f)

    fcntl.lockf(f, fcntl.LOCK_UN)
    f.close()


def persistent_cache(method=False, file_prefix='', file_suffix=''):
    '''Persistent cache decorator.

    It grows indefinitely.
    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.

    '''
    sha = hashlib.sha1()
    def decorator(user_function):
        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            key = (file_prefix,)

            if method:
                key += args[1:]
            else:
                key += args

            if kwds:
                key += tuple(sorted(kwds.items()))

            key += (file_suffix,)

            key = (hashlib.sha224(str(key)).hexdigest(),)

            try:
                result = get_persitent_cache_content(key)
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                wrapper.misses += 1

                set_persitent_cache_content(
                    key, result)         # record this key

            return result

        wrapper.hits = wrapper.misses = 0

        return wrapper

    return decorator

persistent_cache_directory = os.path.expanduser(persistent_cache_directory)
if not os.path.exists(persistent_cache_directory):
    os.makedirs(persistent_cache_directory)

if __name__ == '__main__':
    # pylint: disable-msg=E1101

    print "Testing the LRU and LFU cache decorators."
    print "=" * 120

    print "LRU cache"

    @lru_cache(maxsize=40)
    def f1(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f1(choice(domain), choice(domain))

    print(f1.hits, f1.misses)

    print "LFU cache"

    @lfu_cache(maxsize=40)
    def f2(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f2(choice(domain), choice(domain))

    print(f2.hits, f2.misses)

    print "persistent LRU cache"

    @persistent_cache()
    def f3(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f3(choice(domain), choice(domain))

    print(f3.hits, f3.misses)
