#! /usr/bin/python

import sys, os.path
# Add the directory containing the mturk package to python path
sys.path.append(os.path.abspath("../../bin"))

import datetime

from boto.mturk.question import *
from boto.mturk.qualification import *
from collections import defaultdict

import mturk

n_hits = 100

external_url = "https://SECRET/~jurcicek/2012-09-11-cir-csl/hit_view.py"
frame_height = 2500
EQ = ExternalQuestion(external_url, frame_height)

title = "UFAL - Test an automated tourist information service (it takes 2 minutes on average)"
description = "Rate a speech enabled tourist infomation system."
keywords = "speech,test,voice,evaluation,call,conversation,dialog,dialogue,chat,quick,fast,mark,rate"
reward = 0.20
max_assignments = 1

duration = datetime.timedelta(minutes=100)
lifetime = datetime.timedelta(days=7)
approval_delay = datetime.timedelta(days=1)
                   
q1 = PercentAssignmentsApprovedRequirement('GreaterThan', 90)
q2 = NumberHitsApprovedRequirement('GreaterThan', 10)
q3 = LocaleRequirement('EqualTo', 'US')
qualifications = Qualifications([q1, q2, q3])

response_groups = None

print "Submiting HITs"
conn = mturk.get_connection()

for n in range(n_hits):
  print "Hit #", n
  
  conn.create_hit(question=EQ, lifetime=lifetime, max_assignments=max_assignments, 
    title=title, description=description, keywords=keywords, reward=reward, 
    duration=duration, approval_delay=approval_delay, 
    qualifications=qualifications, response_groups=response_groups)
