#!/usr/bin/env python
# -*- coding: utf-8 -*-
import autopath

import argparse

from collections import defaultdict
from boto.mturk.connection import MTurkConnection

from alex.utils.config import Config

import alex.tools.mturk.bin.mturk as mturk

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Gets account balance at MTURK.

        The program reads the default config in the resources directory
        ('../resources/private/mturk.cfg') and any additional config files passed as
        an argument of a '-c'. The additional config file overwrites any
        default or previous values.

        Remember that the "private" directory is not distributed and it contains
        mainly information that you do not want to share.
      """)

    parser.add_argument('-c', action="store", dest="configs", default=None, nargs='+',
        help='additional configuration file')
    args = parser.parse_args()

    cfg = Config('../../../resources/private/mturk.cfg')
    if args.configs:
        for c in args.configs:
            cfg.merge(c)

    print "Gets MTURK account balance"
    print "-"*120
    print

    conn = MTurkConnection(aws_access_key_id = cfg['MTURK']['aws_access_key_id'],
                           aws_secret_access_key = cfg['MTURK']['aws_secret_access_key'],
                           host = cfg['MTURK']['host'])

    print "Account balance:", conn.get_account_balance()