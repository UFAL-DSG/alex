#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import cgi
import cgitb

print "Content-type: text/html\n\n"
cgitb.enable()

form = cgi.FieldStorage()

p = form.getfirst('p','None')

print """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<HTML>
    <HEAD>
        <TITLE>GAnalytics</TITLE>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>

    </HEAD>
    <BODY>
        <script type="text/javascript">
        var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
        document.write(unescape("%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%3E%3C/script%3E"));
        </script>
        <script type="text/javascript">
        try {
        var pageTracker = _gat._getTracker("UA-349008-12");
        pageTracker._trackPageview('/~fj228/G1/submitted');
        } catch(err) {}</script>
    </BODY>
</HTML>
"""


