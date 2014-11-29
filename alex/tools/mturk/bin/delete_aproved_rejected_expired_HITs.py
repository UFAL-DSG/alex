#!/usr/bin/env python
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import autopath

import argparse
from collections import defaultdict

from boto.mturk.connection import MTurkConnection
from alex.utils.config import as_project_path, Config
import alex.tools.mturk.bin.mturk as mturk

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Delete all approved, rejected or expired hits at MTURK.

        The program reads the default config in the resources directory
        ('../resources/private/mturk.cfg') and any additional config files passed as
        an argument of a '-c'. The additional config file overwrites any
        default or previous values.

        Remember that the "private" directory is not distributed and it contains
        mainly information that you do not want to share.
      """)

    parser.add_argument('-c', "--configs", nargs='+',
                        help='additional configuration files')
    args = parser.parse_args()

    mturk_cfg_fname = as_project_path('resources/private/mturk.cfg')
    cfg = Config.load_configs([mturk_cfg_fname] + args.configs, log=False)

    print "Delete approved, rejected, or expired HITs"

    conn = MTurkConnection(aws_access_key_id = cfg['MTURK']['aws_access_key_id'],
                           aws_secret_access_key = cfg['MTURK']['aws_secret_access_key'],
                           host = cfg['MTURK']['host'])


    for pnum in range(1, 350):
        for hit in conn.get_reviewable_hits(page_size=100, page_number=pnum):
            print "HITId:", hit.HITId

            hitStatus = defaultdict(int)
            for ass in conn.get_assignments(hit.HITId, status='Submitted', page_size=10, page_number=1):
                #print "Dir ass:", dir(ass)

                hitStatus[ass.AssignmentStatus] += 1

            print hitStatus
            if 'Submitted' not in hitStatus:
                print 'Deleting hit:', hit.HITId
                conn.dispose_hit(hit.HITId)
