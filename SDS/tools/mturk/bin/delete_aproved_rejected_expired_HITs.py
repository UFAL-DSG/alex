#! /usr/bin/python

from collections import defaultdict

import mturk

print "Delete aproved, rejected, expired HITs"

conn = mturk.get_connection()

for pnum in range(1, 150):
    for hit in conn.get_reviewable_hits(page_size=100, page_number=pnum):
        print "HITId:", hit.HITId
        
        hitStatus = defaultdict(int)
        for ass in conn.get_assignments(hit.HITId, status = 'Submitted', page_size=10, page_number=1):
            #print "Dir ass:", dir(ass)
            
            hitStatus[ass.AssignmentStatus] += 1 

        print hitStatus
        if 'Submitted' not in hitStatus:
            print 'Deleting hit:', hit.HITId
            conn.dispose_hit(hit.HITId)
        
