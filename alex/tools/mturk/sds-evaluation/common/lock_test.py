#!/usr/bin/env python

# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "Filip"
__date__ = "$12-Nov-2010 17:06:00$"

import utils
import time

if __name__ == "__main__":
    utils.lock()

    for i in range(10):
        print "Sleeping: ", i
        time.sleep(1)

    utils.unlock()

    for i in range(10):
        print "Unlocked: ", i
        time.sleep(1)