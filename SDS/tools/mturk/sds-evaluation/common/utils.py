#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import pickle
import time
import httplib
import urllib
import urlparse
import fcntl

tokenFileName = './mylogdir/tokens.pkl'
workerFileName = './mylogdir/workers.pkl'

lockFile = 0
def lock():
    global lockFile
    lockFile = open('./mylogdir/lock.file', 'w')
    fcntl.lockf(lockFile, fcntl.LOCK_EX)

def unlock():
    fcntl.lockf(lockFile, fcntl.LOCK_UN)
    lockFile.close()
    
def httpPost(url, data):
    # data = {'spam': 1, 'eggs': 2, 'bacon': 0}
    #print url,'\n'
    #print data,'\n'
    
    url = urlparse.urlsplit(url)
    params = urllib.urlencode(data)

    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}
    conn = httplib.HTTPConnection(url[1])
    conn.request("POST", url[2]+"?"+url[3], params, headers)
    response = conn.getresponse()

    print response.status, response.reason

    resp = response.read()
    conn.close()

    return resp

def findTokenTuple(token):
    try:
        lock()
        tm = time.time()

        # load the old pickle
        try:
            pkl_file = open(tokenFileName, 'rb')
            tokens = pickle.load(pkl_file)
        except (IOError, EOFError):
            tokens = []

        try:
            pkl_file.close()
        except:
            pass
    finally:
        unlock()

    # find the token
    for each in tokens:
        if token == "voipheslo" and each[0] == token:
            return each
        # allow only tokens which are not older than 10 minutes
        if each[0] == token and each[2] > (tm - 600):
            return each
        
    return None

def removeToken(tokenTuple):
    try:
        lock()
        tm = time.time()

        # load the old pickle
        try:
            pkl_file = open(tokenFileName, 'rwb')
            tokens = pickle.load(pkl_file)
        except (IOError, EOFError):
            return

        # filter out tokens older than 10 minutes
        tokens = [x for x in tokens if x[2] > tm - 600]
        # remove the requested token
        print "Removing:", tokenTuple
        print "Tokens before:", tokens
        tokens = [x for x in tokens if x != tokenTuple]
        print "Tokens after:", tokens

        # save the updated pickle
        try:
            pkl_file.close()
        except:
            pass

        pkl_file = open(tokenFileName, 'wb')
        pickle.dump(tokens, pkl_file)
        pkl_file.close()
    finally:
        unlock()

def saveToken(token, dialogueID):
    try:
        lock()
        tm = time.time()

        # load the old pickle
        try:
            pkl_file = open(tokenFileName, 'rwb')
            tokens = pickle.load(pkl_file)
        except (IOError, EOFError):
            tokens = []

        # update the pickle
        tokens.append((token,dialogueID,tm))
        # filter out tokens older than 10 minutes
        tokens = [x for x in tokens if x[2] > tm - 600]
        tokens = [x for x in tokens if x[0] != 'voipheslo']
        tokens.append(('voipheslo','/data/dial/classic/Aug09VoIP-CamInfo/voipheslo',tm))

        # save the updated pickle
        try:
            pkl_file.close()
        except:
            pass

        pkl_file = open(tokenFileName, 'wb')
        pickle.dump(tokens, pkl_file)
        pkl_file.close()
    finally:
        unlock()

def saveWorker(workerID, phone):
    try:
        lock()
        tm = time.time()

        # load the old pickle
        try:
            pkl_file = open(workerFileName, 'rwb')
            workers = pickle.load(pkl_file)
        except (IOError, EOFError):
            workers = []

        # update the pickle
        workers.append((workerID,tm,phone))
        # filter out workers older than 4 weeks
        workers = [x for x in workers if x[1] > tm - 60*60*24*7*4]

        # save the updated pickle
        try:
            pkl_file.close()
        except:
            pass

        pkl_file = open(workerFileName, 'wb')
        pickle.dump(workers, pkl_file)
        pkl_file.close()
    finally:
        unlock()

def verifyWorker(workerID):
    try:
        lock()
        tm = time.time()

        # load the old pickle
        try:
            pkl_file = open(workerFileName, 'rb')
            workers = pickle.load(pkl_file)
        except (IOError, EOFError):
            workers = []

        try:
            pkl_file.close()
        except:
            pass
    finally:
        unlock()

    # find the phones of a particular worker
    phones = [x[2] for x in workers if x[0] == workerID]
    # find workers using the previous phones
    phonesWorkers = [x[0] for x in workers if x[2] in phones]

    numberSubmitions24h = 0
    numberSubmitions4w = 0
    for each in workers:
        # allow only tokens which are not older than 24 hours
        if each[0] in phonesWorkers and each[1] > (tm - 60*60*24):
            numberSubmitions24h += 1

        # allow only tokens which are not older than 4 weekss
        if each[0] in phonesWorkers and each[1] > (tm - 60*60*24*7*4):
            numberSubmitions4w += 1

    if numberSubmitions24h > 20:
        return ">20in24h"
    elif numberSubmitions4w > 40:
        return ">40in4w"

    return "OK"

