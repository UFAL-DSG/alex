#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Filip Jurcicek"
__date__ = "$08-Mar-2010 13:45:34$"

import cgi
import os

print "Content-type: text/html"
print ""

print cgi.escape(os.environ["REMOTE_ADDR"])