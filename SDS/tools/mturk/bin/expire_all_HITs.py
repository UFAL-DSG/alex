#! /usr/bin/python

from collections import defaultdict
from boto.mturk.connection import MTurkConnection

print "Expire all HITs"

def printAssignment(ass):
    print '-'*100
    print 'AcceptTimeass:', ass.AcceptTime
    print 'AssignmentId:', ass.AssignmentId
    print 'AssignmentStatus:', ass.AssignmentStatus
    print 'HITId:', ass.HITId
    print 'WorkerId:', ass.WorkerId
    
#conn = MTurkConnection(aws_access_key_id='your_aws_access_key_id')
conn = MTurkConnection(aws_access_key_id='your_aws_access_key_id')

for pnum in range(1, 50):
    for hit in conn.search_hits(page_size=100, page_number=pnum):
        print "HITId:", hit.HITId
        
        hitStatus = defaultdict(int)
        for ass in conn.get_assignments(hit.HITId, status = 'Submitted', page_size=10, page_number=1):
            #print "Dir ass:", dir(ass)
            
            hitStatus[ass.AssignmentStatus] += 1 

        print hitStatus
        print 'Expiring hit:', hit.HITId
        conn.expire_hit(hit.HITId)
        
