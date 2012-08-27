#! /usr/bin/python

from boto.mturk.connection import MTurkConnection

workerId = 'A1CV0GNA8DHF6J'
feedback = 'You are not a native speaker of English.'

print "Reject HITs from the worker:", workerId

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
    for hit in conn.get_reviewable_hits(page_size=100, page_number=pnum):
#       print "HITId:", hit.HITId
        
        for ass in conn.get_assignments(hit.HITId, status = 'Submitted', page_size=10, page_number=1):
            #print "Dir ass:", dir(ass)
            
#            if ass.AssignmentStatus not in ['Approved', 'Rejected', 'Submitted']:

            if ass.WorkerId == workerId:
                printAssignment(ass)
                print "- "*50
                print "Rejecting assignment:", ass.AssignmentId
                conn.reject_assignment(ass.AssignmentId, feedback)
                print "- "*50


print "To block the worker use: requester.mturk.com/bulk/workers/%s" % workerId
