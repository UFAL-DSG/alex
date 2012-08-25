#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import cgi
import cgitb

import sys
if '' not in sys.path:
    sys.path.append('')
from utils import *

print "Content-type: text/html\n\n"
cgitb.enable()

form = cgi.FieldStorage()
token = str(form.getfirst('token','None'))

# private test
if token == "voipheslo":
    print "Valid"
elif findTokenTuple(token):
    print "Valid"
else:
    print "Invalid"
