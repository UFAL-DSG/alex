#!/usr/bin/env python

# SIP call transfer application.
#
# Copyright (C) 2003-2008 Filip Jurcicek <filip.jurcicek@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import sys
import pjsua as pj
import threading
import sqlite3
import random
import copy
import time

domain='your_domain'
user='your_user'
password='your_password'

destinations = ["sip:4366@SECRET:5066",
                "sip:4279@SECRET:5066"]

destPriorities = {"sip:4366@SECRET:5066": 1,
                  "sip:4279@SECRET:5066": 1,
                 }

conn = sqlite3.connect('./call_counts.sqlite3')

call_counts = sqlite3.connect('./call_counts.sqlite3')
# Create table
call_counts.execute('''CREATE TABLE IF NOT EXISTS call_counts (caller text, destination text)''')
call_counts.commit()
call_counts.close()

def findLeastCalledDestination(caller):
    call_counts = sqlite3.connect('./call_counts.sqlite3')
    c = call_counts.cursor()
    c.execute('''SELECT caller, destination, count(destination) as numcalls
                FROM call_counts
                WHERE caller=?
                GROUP BY destination
                ORDER BY numcalls ASC''', (caller, ))

    userDestinations = {}
    minCalls = 99999
    minDestinations = []
    print
    print 'Caller                                             Destinations                            #calls'
    print '-'*100
    for row in c:
        print row[0], " | ", row[1], " | ", row[2]
        userDestinations[row[1]] = row[2]
        minCalls = min(minCalls, row[2])
        if minCalls == row[2]:
            minDestinations.append(row[1])

    call_counts.close()

    missingDestinations = list(set(destinations) - set(userDestinations.keys()))
    if len(missingDestinations):
        return random.choice(missingDestinations)

    # this is a hack due to a threading problem
    minDestinations = list(set(destinations) - (set(destinations) - set(minDestinations)))
    # reflect the sampling priorities
    minDestNew = []
    for destination in minDestinations:
        minDestNew.extend([destination,]*destPriorities[destination])
    minDestinations = sorted(minDestNew)

    print "Randomly selecting among: "
    print " - ", ', '.join(minDestinations)

    return random.choice(minDestinations)

def addCallTransfer(caller, destination):
    call_counts = sqlite3.connect('./call_counts.sqlite3')
    c = call_counts.cursor()
    c.execute('''INSERT INTO call_counts VALUES (?,?)''', (caller, destination))
    call_counts.commit()
    call_counts.close()


# Callback to receive events from account
class MyAccountCallback(pj.AccountCallback):
    sem = None

    def __init__(self, account=None):
        pj.AccountCallback.__init__(self, account)

    # Notification on incoming call
    def on_incoming_call(self, call):
        print "Incoming call from ", call.info().remote_uri

        call_cb = MyCallCallback(call)
        call.set_callback(call_cb)

        call.answer()

    def wait(self):
        self.sem = threading.Semaphore(0)
        self.sem.acquire()

    def on_reg_state(self):
        if self.sem:
            if self.account.info().reg_status >= 200:
                self.sem.release()


# Callback to receive events from Call
class MyCallCallback(pj.CallCallback):

    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)

    # Notification when call state has changed
    def on_state(self):
        print "MyCallCallback::on_state : Call with", self.call.info().remote_uri,
        print "is", self.call.info().state_text,
        print "last code =", self.call.info().last_code,
        print "(" + self.call.info().last_reason + ")"

        if self.call.info().state == pj.CallState.CONFIRMED:
            destination = findLeastCalledDestination(self.call.info().remote_uri)
            addCallTransfer(self.call.info().remote_uri, destination)
            print
            print "="*80
            print "Transferring:", self.call.info().remote_uri, " to:", destination
            print "="*80
            print
            self.call.transfer(destination)

    def on_transfer_status(self, code, reason, final, cont):
        print "MyCallCallback::on_transfer_status : Call with", self.call.info().remote_uri,
        print "is", self.call.info().state_text,
        print "last code =", self.call.info().last_code,
        print "(" + self.call.info().last_reason + ")"

        print code, reason, final, cont

        #self.call.hangup()

        return True

    def on_transfer_request(self, dst, code):
        print "MyCallCallback::on_transfer_request Remote party transferring the call to ",
        print dst, code

        return 202

    # Notification when call's media state has changed.
    def on_media_state(self):
        if self.call.info().media_state == pj.MediaState.ACTIVE:
            # Connect the call to sound device
            call_slot = self.call.info().conf_slot
            pj.Lib.instance().conf_connect(call_slot, 0)
            pj.Lib.instance().conf_connect(0, call_slot)
            print "Media is now active"
        else:
            print "Media is inactive"

    def on_dtmf_digit(self, digits):
      print "Received digits:", digits

# Function to make call
def make_call(acc, uri):
    try:
        print "Making call to", uri
        return acc.make_call(uri, cb=MyCallCallback())
    except pj.Error, e:
        print "Exception: " + str(e)
        return None

try:
    # Create library instance
    lib = pj.Lib()

    # Init library with default config and some customized
    # logging config.
    lib.init(log_cfg = pj.LogConfig(level=LOG_LEVEL, callback=log_cb))
    lib.set_null_snd_dev()

    # Create UDP transport which listens to any available port
    transport = lib.create_transport(pj.TransportType.UDP)  # pj.TransportConfig(5080)
    print
    print "Listening on", transport.info().host,
    print "port", transport.info().port, "\n"

    # Start the library
    lib.start()

    acc = lib.create_account(pj.AccountConfig(domain, user, password))

    acc_cb = MyAccountCallback(acc)
    acc.set_callback(acc_cb)
    acc_cb.wait()

    print
    print
    print "Registration complete, status=", acc.info().reg_status,  "(" + acc.info().reg_reason + ")"

    my_sip_uri = "sip:" + transport.info().host + ":" + str(transport.info().port)

#    time.sleep(2)
#    make_call(acc, "sip:4366@SECRET:5066")

    # Menu loop
    while True:
        print "="*80
        print "My SIP URI is", my_sip_uri
        print "Menu:  q=quit"

        input = sys.stdin.readline().rstrip("\r\n")
        if input == "q":
            break

    # Shutdown the library
    transport = None
    acc.delete()
    acc = None
    lib.destroy()
    lib = None

except pj.Error, e:
    print "Exception: " + str(e)
    lib.destroy()
    lib = None

