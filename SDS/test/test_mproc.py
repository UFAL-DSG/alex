#!/usr/bin/env python
# -*- coding: utf-8 -*-

import multiprocessing

import __init__

from SDS.utils.mproc import local_lock, global_lock

if __name__ == "__main__":
    class TestLocalLock:
        var = 0

        @local_lock()
        def inc_var(self):
            self.var += 1
            return self.var

    class TestGlobalLock:
        lock = multiprocessing.Lock()
        var = 0

        @global_lock(lock)
        def inc_var_1(self):
            self.var += 1
            return self.var

        @global_lock(lock)
        def inc_var_2(self):
            self.var += 2
            return self.var


    t1 = TestLocalLock()
    t1.inc_var()
    t1.inc_var()
    print t1.var

    t2 = TestGlobalLock()
    t2.inc_var_1()
    t2.inc_var_2()
    print t2.var
