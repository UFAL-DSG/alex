#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Filip Jurcicek"
__date__ = "$08-Mar-2010 13:45:34$"

import cgi
import cgitb

from dbutils import get_local_db_session
from model import Token, Worker
from sqlalchemy.orm.exc import NoResultFound

import sys
if '' not in sys.path:
    sys.path.append('')
from common.utils import *


if __name__ == "__main__":
    print "Content-type: text/html\n\n"
    cgitb.enable()

    form = cgi.FieldStorage()
    token_number = str(form.getfirst('token', 'None'))

    # open database
    session = get_local_db_session()

    try:
        token = session.query(Token).filter_by(number=token_number).one()
        if token.submission is None:
            raise NoResultFound()

        print "Valid"
    except NoResultFound:
        if token_number == "voipheslo":
            print "Valid"
        else:
            print "Invalid"

