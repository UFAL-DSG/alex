#! /usr/bin/python

import mturk

workerId = 'A1CV0GNA8DHF6J'
feedback = 'You are not a native speaker of English.'

print "Reject HITs from the worker:", workerId

conn = mturk.get_connection()

for pnum in range(1, 50):
    for hit in conn.get_reviewable_hits(page_size=100, page_number=pnum):
#       print "HITId:", hit.HITId

        for ass in conn.get_assignments(hit.HITId, status = 'Submitted', page_size=10, page_number=1):
            #print "Dir ass:", dir(ass)

            if ass.WorkerId == workerId:
                printAssignment(ass)
                print "- "*50
                print "Rejecting assignment:", ass.AssignmentId
                conn.reject_assignment(ass.AssignmentId, feedback)
                print "- "*50


print "To block the worker use: requester.mturk.com/bulk/workers/%s" % workerId
