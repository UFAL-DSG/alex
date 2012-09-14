#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="Filip Jurcicek"
__date__ ="$08-Mar-2010 13:45:34$"

import xml.dom.minidom
import re
import random
from xml.dom.minidom import Node

import cgi
import cgitb
cgitb.enable()

import sys
if '' not in sys.path:
    sys.path.append('')
from common.utils import *

task_xml_filename = "../CIRtasks_V7.xml"

def include(fileName):
    f = open(fileName, "r")

    print "<!-- include('", fileName,"') -->"
    for line in f:
        print line,

def getTextFromNode(node):
    text = ""
    for n in node.childNodes:
      if n.nodeType == Node.TEXT_NODE:
        text += n.data

    text = text.strip()
    text = re.sub("\s+" , " ", text)
   
    return text

def getTask():
    """
    The function loads an xml file with the task specifications and randomly
    selects one of the tasks.
    """
    random.seed()
    
    try:
        doc = xml.dom.minidom.parse(task_xml_filename)
        tasks = doc.getElementsByTagName("task")

        # sample the task
        i = random.randint(0,len(tasks)-1)
        node = tasks[i]
        goal = getTextFromNode(node.getElementsByTagName("goal")[0])
        task = getTextFromNode(node.getElementsByTagName("text")[0])
    except Exception, e:
        print e
        
        goal = "inform(food=French);request(name,phone)"
        task = "You are thinking of having some French food later, so you want" +\
               "to get the name and phone number of a suitable restaurant."

    goal = goal.replace('"','\\"')
    return goal, task

def getPhone():
    # the multiple phones are not necessary anymore as the PBX randomly distribute the calls among the tested systems
    phones = ["1-888-826-5115",]
    return random.choice(phones)

form = cgi.FieldStorage()

print "Content-type: text/html\n\n"

print """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<HTML>
    <HEAD>
        <TITLE>Amazon Mechanical Turk - Cambridge Information System</TITLE>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>

        <link rel="stylesheet" href="common/mturk.css" TYPE="text/css" MEDIA="screen">
        <script type="text/javascript" src="common/tabber-minimized.js"></script>
        <script type="text/javascript" src="common/jquery-1.4.2.min.js"></script>
        <script type="text/javascript" src="common/feedback.js"></script>
        <script type="text/javascript" src="common/submitFeedback.js"></script>
        
        <script type="text/javascript">
            /* Optional: Temporarily hide the "tabber" class so it does not "flash"*/
            document.write('<style type="text/css">.tabber{display:none;}<\/style>');
        </script>
        <script type="text/javascript" src="https://www.google.com/jsapi?key=ABQIAAAA-fK3SsIXeXJuKpgW1hT6kRRwPF2u2lm2QTXas2nGIPxzsfKaMRRV4qNXAn_UlCjcNRodB7mb2gBIVw"></script>
        <script>
            google.load("search", "1",{callback: getLocation});
            var glocation = "";
            function getLocation() {
                if (google.loader.ClientLocation) {
                    glocation += google.loader.ClientLocation.address.country_code;
                    glocation += ":";
                    glocation += google.loader.ClientLocation.address.region;
                    glocation += ":";
                    glocation += google.loader.ClientLocation.address.city;
                }

                if (glocation.lastIndexOf('US', 0) != 0) {
                    document.getElementById("locationWarning").innerHTML = "This HIT can be completed only by native speakers of English from USA. If it is found that this HIT was completed from other location than USA then it will be automatically rejected.";
                }
            }
        </script>
    </HEAD>
    <BODY onload="tabberAutomatic();disableFeedback();" >
    <!--
    <BODY onload="tabberAutomatic();" >
    -->
    <script type="text/javascript">

      var _gaq = _gaq || [];
      _gaq.push(['_setAccount', 'UA-349008-15']);
      _gaq.push(['_trackPageview']);

      (function() {
        var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
        ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
        var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
      })();

    </script>
"""

print '<H2 style="color:red;" id="locationWarning"></H2><BR>'

status = None
assignmentId = form.getfirst('assignmentId','None')
workerId = form.getfirst('workerId','None')
hitId = form.getfirst('hitId','None')
goal = 'None'
task = 'None'

print """
<script>
  if (document.referrer.lastIndexOf("sandbox") >= 0) {
    document.write('<H2 style="color:red;">This is a SANDBOX HIT.</H2><BR>')
    var sandbox = true;
  } 
  else {
    var sandbox = false;
  }
</script>
"""

if assignmentId == 'ASSIGNENT_ID_NOT_AVAILABLE':
    status = "preview"
    print '<H2 style="color:red;">This is a preview of the HIT. Accept the HIT before you call the service.</H2><BR>'
elif assignmentId == 'None':
    status = "test"
    print '<H2 style="color:red;">This page is not loaded from MTURK.</H2>'
else:
    status = "accepted"
    # assignmentId was provided

if not workerId == 'None':
    vw = verifyWorker(workerId)
    if vw == ">20in24h":
        print """<H2 style="color:red;">You have submitted more than 20 HITs in the
        last 24 hours. You are welcome to come after 24 hours and do another 20 HITs.
        Please, bookmark the following
        <a target="_top" href="https://www.mturk.com/mturk/searchbar?searchWords=automated+tourist+information">
        link on MTURK search</a>. </H2>
        </BODY>
    <HTML>
    """
        sys.exit()

    if vw == ">40in4w":
        print """<H2 style="color:red;">You have submitted more than 40 HITs in the
        last four weeks. You are welcome to come after four weeks and do another 40 HITs.
        Please, bookmark the following
        <a target="_top" href="https://www.mturk.com/mturk/searchbar?searchWords=automated+tourist+information">
        link on MTURK search</a>. </H2>
        </BODY>
    <HTML>
    """
        sys.exit()

# default goal and task
goal, task = getTask()
phone = getPhone()

print """
<script>
    var task = "%(task)s";
    var goal = "%(goal)s";
    var assignmentId = "%(assignmentId)s";
    var workerId = "%(workerId)s";
    var hitId = "%(hitId)s";

</script>
""" % {'task':task, 'goal':goal, 'assignmentId':assignmentId, 'workerId':workerId, 'hitId':hitId}

print """
        <img src="common/UNIBAN-S.gif" style="float:left;margin:5px;" height="100">
        <img src="common/ENGBAN-S.gif" style="float:right;margin:5px;" height="100">
        <H2 style="padding-left:100px;padding-right:100px;text-align:center;">
            Evaluate and rate automated tourist information service
        </H2>
        <br/>
        <br/>
        <br/>

        <div class="tabber" id="mytab1">
        <div class="tabbertab">
        <h2>Intro</h2>
            <div>
            <img src="common/mturk-computer-headset.png" width="200" height="200"
            style="float:right;margin:15px;">
            <p>
                This HIT requires you to <b>talk naturally</b> to an automated tourist
                information service for Cambridge in the UK (you don't have to know
                anything about Cambridge). You must be a <b>native</b>
                English speaker. To complete the HIT, you must call a USA toll free
                phone number: <b>%(phone)s</b>. If you call from a USA land line,
                than the calls should be completely free.
            </p>
            <p>
                You must be a <b>NATIVE</b> speaker of English (with UK, USA, Canadian, Australian, or South African accents).
            </p>
            <p>
                When you call the provided toll free phone number, you will be
                connect with the automated tourist information service.
                Please, try to talk about the
                topic which is presented in the green box below.
                Once you get the required information, you can finish
                the call by saying <span style="color: red;">"Thank you. Good bye."</span> to the system.
                At the end of the call, the system will give you a
                <b>four digit code</b> which you have to enter into the feedback form.
                This is used to verify the genuine HIT submissions.
            </p>
            <!--<p>
                When you call the provided toll free phone number, you will be 
                connect with the automated tourist information service. 
                Please, try to talk about the topic which is presented in the green box below. 
                Once you get the required information, you can finish the call 
                by saying "Thank you. Good bye." to the system. 
                The system will then ask you to press 1 if you were satisfied and 0 if you were not satisfied. 
                Once you do that, the system will give you a <b>four digit code</b> which you have to enter into the feedback form. 
                This is used to verify the genuine HIT submissions.
            </p>-->
            <p>
                <b> Once the call is finished, please fill in the feedback form.
                Please enter the provided code, answer the questions
                and submit the results.
                The feedback is very important as only the calls with
                completed feedback and the correct code will be approved. </b>
            </p>
            <!--<p>
                Be patient -- the system may make an error on purpose. However, if you cannot get all requested information,
                end the call by saying "Thank you. Good bye." Such calls are valid and are accepted.
                Remember to press 1 or 0 to indicate your satisfaction and wait for the code!
            </p>-->
            <!--<p>
                If you cannot get all requested information <b>in less than 3 minutes</b>, 
                end the call by saying <span style="color: red;">"Thank you. Good bye."</span>
                Such calls are valid and are accepted.
                Remeber to wait for the code!
            </p>-->
            <p style="color:red;font-weight: bold;">
                All data is collected anonymously and by
                <a href="http://ufal.mff.cuni.cz/">
                the Institute of Formal and Applied Linguistics, Charles University in Prague</a>.
            </p>
            <p>
                PLEASE READ THE INSTUCTIONS BEFORE YOU PARTICIPATE IN THIS
                HIT FOR THE FIRST TIME
            </p>
            <p>
                Also, submit <b>a maximum 20 HITs in one day</b>.
                You are welcome to come the next day and do another 20 HITs.
                Please do not submit more than 40 HITs in total.
                You can bookmark the following <a target="_top" href="https://www.mturk.com/mturk/searchbar?searchWords=UFAL+automated+tourist+information">
                link on MTURK search</a>.
            </p>
            <!--<p style="color:red;">
                Please, submit at <b>least 5 HITs</b> in total as we are testing 5 different telephone systems.
                It would be very helpfull if you tested all of the systems and gave us your oppinion on all of them.
                If you could submit <b>more than  10 HITs</b> then it would be even better!
            </p>-->
            </div>
        </div>
        <div class="tabbertab">
""" % {'phone':phone}
include('mturk-instructions.html')
print """
        </div>
        <div class="tabbertab">
"""
include('common/mturk-example1.html')
print """
        </div>
        <div class="tabbertab">
"""
include('common/mturk-consent.html')
print """
        </div>
        </div>
"""
# no poll for now
#if status != "test":
#    include('common/mturk-poll.html')
print """
        <p>
            <strong> Please try to talk about the following topic: </strong>
        </p>
        <div class=task>
            <strong>%(task)s</strong>
        </div>
     
""" % {'task':task}

if assignmentId == 'ASSIGNMENT_ID_NOT_AVAILABLE':
    print """
        <div align="center">
        <div class=warning style="color:red;">
            This is a preview of the HIT. Accept the HIT before you call the service.
        </div>
        </div>
"""
    
print """
        <div align="center">
        <div class=warning>
            To complete the HIT, call this toll free phone number: (USA) <b>%(phone)s</b>
        </div>
"""  % {'phone':phone}
print """
        <div class=feedback>
        <form>
            Enter the code: <input id="token" type="text" name="token" onkeyup="validateToken(this.value)" />
            <span id="tokenvalid"></span>
        </form>

        <form id="feedback" name="feedback" >
            <b style="text-decoration:underline;font-size: 130%"> Please state your attitude towards the following statements</b>
            <br/>
            <div id="feedback-error"></div>
            <br/>
            <b> Did you find all the information you were looking for?</b>
            <br/>
            <br/>
            <input type="radio" name="Q1" value="Yes"/> <label>Yes</label>
            <input type="radio" name="Q1" value="No"/> <label>No</label>
            <br/>
            <br/>
            <b> The system understood me well.</b>
            <br/>
            <br/>
            <input type="radio" name="Q2" value="strongly disagree"/><label>strongly disagree</label>
            <input type="radio" name="Q2" value="disagree"/><label>disagree</label>
            <input type="radio" name="Q2" value="lightly disagree"/><label>lightly disagree</label>
            <input type="radio" name="Q2" value="slightly agree"/><label>slightly agree</label>
            <input type="radio" name="Q2" value="agree"/><label>agree</label>
            <input type="radio" name="Q2" value="strongly agree"/><label>strongly agree</label>
            <br/>
            <br/>
            <b> The phrasing of the system's responses was good.</b>
            <br/>
            <br/>
            <input type="radio" name="Q3" value="strongly disagree"/><label>strongly disagree</label>
            <input type="radio" name="Q3" value="disagree"/><label>disagree</label>
            <input type="radio" name="Q3" value="lightly disagree"/><label>lightly disagree</label>
            <input type="radio" name="Q3" value="slightly agree"/><label>slightly agree</label>
            <input type="radio" name="Q3" value="agree"/><label>agree</label>
            <input type="radio" name="Q3" value="strongly agree"/><label>strongly agree</label>
            <br/>
            <br/>
            <b> The system's voice was of good quality.</b>
            <br/>
            <br/>
            <input type="radio" name="Q4" value="strongly disagree"/><label>strongly disagree</label>
            <input type="radio" name="Q4" value="disagree"/><label>disagree</label>
            <input type="radio" name="Q4" value="lightly disagree"/><label>lightly disagree</label>
            <input type="radio" name="Q4" value="slightly agree"/><label>slightly agree</label>
            <input type="radio" name="Q4" value="agree"/><label>agree</label>
            <input type="radio" name="Q4" value="strongly agree"/><label>strongly agree</label>
            <br/>
            <br/>
            <br/>
            <b>  General comments (optional)</b>
            <br/>
            <br/>
            <textarea name="comments" rows=4 cols=60></textarea>
            <br/>
            <br/>
            <!--
            <b>  Contact info (optional)</b>
            <br/>
            <br/>
            <input type="text" name="contact"/>
            <br>
            <br>
            -->
            <button type=button name="submit" class=submit onclick="submitFeedback();">Submit the HIT</button>
        </form>

        </div>
        </div>
"""
    
#include('common/mturk-comments.html')
# print """
#        <p>
#            If you have any problems, you can find help
#            <A href="javascript:document.getElementById('mytab1').tabber.tabShow(4)">here.</A>
#        </p>
#"""

if assignmentId == "ASSIGNMENT_ID_NOT_AVAILABLE":
    print """<script>disableToken();</script>"""

print """
    </BODY>
</HTML>
""" 
