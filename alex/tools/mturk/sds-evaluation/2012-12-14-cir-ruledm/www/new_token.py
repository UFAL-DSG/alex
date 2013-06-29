#!/usr/bin/env python

import cgi
import cgitb
import sys
import os

sys.path.insert(0, '')

from local_cfg import cfg
token_file = cfg['token_file']

from model import Token
from dbutils import get_local_db_session

if __name__ == "__main__":
    print "Content-type: text/html\n\n"
    
    form = cgi.FieldStorage()
    data = str(form.getfirst('data', 'None'))

    session = get_local_db_session()
    
    cgitb.enable()

    token, submission = Token.get_new(session)
    if token is None:
        Token.generate_tokens(session)
        token, submission = Token.get_new(session)
    submission.dialogue_id = data
    session.commit()

    print token.number 