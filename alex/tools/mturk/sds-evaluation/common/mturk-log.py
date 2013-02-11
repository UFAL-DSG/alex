#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Filip Jurcicek"
__date__ = "$08-Mar-2010 13:45:34$"

import cgi
import cgitb
import os.path
import os

print "Content-type: text/html\n\n"
cgitb.enable()

form = cgi.FieldStorage()

dialogueID = form.getfirst('dialogueID', 'None')
xmlFeedback = form.getfirst('xmlFeedback', 'None')
xmlDialogueLog = form.getfirst('xmlDialogueLog', 'None')

print 'dialogueID:', dialogueID

dialogueID = os.path.split(dialogueID)[-1]

try:
    if dialogueID.startswith('voip') and not '.' in dialogueID:
        os.mkdir(os.path.join('mylogdir', dialogueID))
        print 'dialogue directory created:', dialogueID

        f = open(os.path.join('mylogdir', dialogueID, 'feedback.xml'), 'w')
        f.write(xmlFeedback)
        f.close()
        print 'fedback.xml written'

        f = open(
            os.path.join('mylogdir', dialogueID, 'webDialogueLog.xml'), 'w')
        f.write(xmlDialogueLog)
        f.close()
        print 'webDialogueLog.xml written'

    else:
        print 'Invalid dialogueID'
except OSError:
    print 'OSError: Invalid dialogueID'
