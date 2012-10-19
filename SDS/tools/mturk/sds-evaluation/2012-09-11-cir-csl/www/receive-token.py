#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import cgi
import cgitb

import sys
if '' not in sys.path:
    sys.path.append('')
from common.utils import *

print "Content-type: text/html\n\n"

cgitb.enable()

form = cgi.FieldStorage()
token = str(form.getfirst('token','None'))
dialogueID = str(form.getfirst('dialogueID','None'))
dialogueID = dialogueID.replace("//","/")             # fix an error in the AHub.cpp

saveToken(token, dialogueID)

print "Token and dialogueID saved."
