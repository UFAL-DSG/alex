#! /usr/bin/python

from collections import defaultdict

import mturk

print "Aprove all outstanding HITs"

conn = mturk.get_connection()

for pnum in range(1, 50):
    for hit in conn.get_reviewable_hits(page_size=100, page_number=pnum):
        print "HITId:", hit.HITId

        for ass in conn.get_assignments(hit.HITId, status = 'Submitted', page_size=10, page_number=1):
            #print "Dir ass:", dir(ass)

            if ass.AssignmentStatus == 'Submitted':
                mturk.print_assignment(ass)

                print "-"*100
                print "Approving the assignment"
                conn.approve_assignment(ass.AssignmentId)
                print "-"*100
