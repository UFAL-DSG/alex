#! /usr/bin/python

from boto.mturk.connection import MTurkConnection


def get_connection():
    conn = MTurkConnection(aws_access_key_id='your_aws_access_key_id')

    return conn


def print_assignment(ass):
    print '-' * 100
    print 'AcceptTimeass:', ass.AcceptTime
    print 'AssignmentId:', ass.AssignmentId
    print 'AssignmentStatus:', ass.AssignmentStatus
    print 'HITId:', ass.HITId
    print 'WorkerId:', ass.WorkerId
