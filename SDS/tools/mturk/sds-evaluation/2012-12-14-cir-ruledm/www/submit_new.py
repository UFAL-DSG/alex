#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Filip Jurcicek"
__date__ = "$08-Mar-2010 13:45:34$"

import cgi
import cgitb
import os.path
import os
import datetime

import sys
if '' not in sys.path:
    sys.path.append('')
from common.utils import *

from dbutils import get_local_db_session
from model import Token, Worker
from sqlalchemy.orm.exc import NoResultFound


def get_worker_id(xml_feedback):
    i = xml_feedback.find("<workerId>")
    ii = xml_feedback.find("</workerId>")

    if i != -1 and ii != -1:
        id = xml_feedback[i + len("<workerId>"):ii].strip()
        return id

    return ""


def main():
    print "Content-type: text/html\n\n"
    cgitb.enable()

    # process input
    form = cgi.FieldStorage()
    xml_feedback = form.getfirst('xmlFeedback', 'None')
    token_number = form.getfirst('token', 'None')

    # open database
    session = get_local_db_session()

    try:
        token = session.query(Token).filter_by(number=token_number).one()
    except NoResultFound:
        print "KO"
        return

    # insert the retrived dialogueID into the xmlFeedback
    xml_feedback = xml_feedback.replace("<dialogueId></dialogueId>", "<dialogueId>" + token.submission.dialogue_id + "</dialogueId>")
    worker_id = get_worker_id(xml_feedback)
    phone = token.submission.dialogue_id.rsplit("-", 1)[1]

    try:
        curr_worker = session.query(Worker).filter_by(worker_id=worker_id).one()
    except NoResultFound:
        curr_worker = Worker(worker_id=worker_id, phone_number=phone)
        session.add(curr_worker)

    # save submitted data
    submission = token.submission
    submission.data = xml_feedback
    submission.worker = curr_worker
    submission.timestamp = datetime.datetime.now()

    # free token
    token.submission = None

    session.commit()

if __name__ == "__main__":
    main()
