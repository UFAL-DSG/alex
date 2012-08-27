#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import cgi
import cgitb
import os.path
import os

import sys
if '' not in sys.path:
    sys.path.append('')
from common.utils import *

def getWorkerID(xmlFeedback):
    i = xmlFeedback.find("<workerId>")
    ii = xmlFeedback.find("</workerId>")

    if i != -1 and ii != -1:
        id = xmlFeedback[i+len("<workerId>"):ii].strip()
        return id

    return ""

print "Content-type: text/html\n\n"
cgitb.enable()

form = cgi.FieldStorage()

#for k in form:
#    print "Variable:", k , "Value:", form[k].value
#print

xmlFeedback = form.getfirst('xmlFeedback','None')
token = form.getfirst('token','None')
print 'token:', token
tokenTuple = findTokenTuple(token)

if tokenTuple:
    # get dialogueID based on the token
    dialogueID = tokenTuple[1]
    print 'tokenTuple:', tokenTuple
    print 'dialogueID:', dialogueID
    print 'xmlFeedback:', xmlFeedback

    dialogueIDLastPart = os.path.split(dialogueID)[-1]

    # insert the retrived dialogueID into the xmlFeedback
    xmlFeedback = xmlFeedback.replace("<dialogueId></dialogueId>", "<dialogueId>"+dialogueID+"</dialogueId>")
    
    workerID = getWorkerID(xmlFeedback)
    phone = os.path.split(dialogueID)[1].replace("voip-", "")
    phone = phone[:phone.index("-")]

    saveWorker(workerID, phone)
    
    # save the feedback locally
    print "Saving locally"
    try:
        if dialogueIDLastPart.startswith('voip') and not '.' in dialogueID:
            os.mkdir(os.path.join('mylogdir',dialogueIDLastPart))
            print 'dialogue directory created:', dialogueIDLastPart

            f = open(os.path.join('mylogdir',dialogueIDLastPart, 'feedback.xml'),'w')
            f.write(xmlFeedback)
            f.close()
            print 'fedback.xml written'

        else:
            print 'Invalid dialogueID'
    except OSError:
        print 'OSError: Invalid dialogueID'


    # submit the feedback back to the voiphub (dialogue manager)
    print "Submitting to ./voiphub"
    print httpPost("http://SECRET/demo-log.php",
                    {'dialogueID': dialogueID,
                     'xmlFeedback': xmlFeedback})

    # remove the used token
    removeToken(tokenTuple)
else:
    print 'Invalid token'
