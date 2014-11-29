#!/usr/bin/env python
if __name__ == '__main__':
    import autopath

import argparse
import sys
import os.path
import datetime
from collections import defaultdict

from boto.mturk.connection import MTurkConnection
from boto.mturk.question import *
from boto.mturk.qualification import *

import alex.tools.mturk.bin.mturk as mturk
from alex.utils.config import as_project_path, Config

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Submitting HITs to MTURK.

        The program reads the default config in the resources directory
        ('../resources/private/mturk.cfg') and any additional config files passed as
        an argument of a '-c'. The additional config file overwrites any
        default or previous values.

        Remember that the "private" directory is not distributed and it contains
        mainly information that you do not want to share.
      """)

    parser.add_argument('-c', "--configs", nargs='+',
                        help='additional configuration files')
    parser.add_argument('-n', '--nhits', default=1, type=int,
                        help='number of HITs')
    args = parser.parse_args()

    mturk_cfg_fname = as_project_path('resources/private/mturk.cfg')
    cfg = Config.load_configs([mturk_cfg_fname] + args.configs, log=False)

    conn = MTurkConnection(aws_access_key_id = cfg['MTURK']['aws_access_key_id'],
                           aws_secret_access_key = cfg['MTURK']['aws_secret_access_key'],
                           host = cfg['MTURK']['host'])

    n_hits = args.nhits

    external_url = "https://SECRET/~zilka/2012-12-14-cir-ruledm/hit_view.py"
    frame_height = 2500
    EQ = ExternalQuestion(external_url, frame_height)

    title = "UFAL - Test an automated tourist information service (it takes 2 minutes on average)"
    description = "Rate a speech enabled tourist infomation system."
    keywords = "speech,test,voice,evaluation,call,conversation,dialog,dialogue,chat,quick,fast,mark,rate"
    reward = 0.20
    max_assignments = 1

    duration = datetime.timedelta(minutes=100)
    lifetime = datetime.timedelta(days=7)
    approval_delay = datetime.timedelta(days=1)

    q1 = PercentAssignmentsApprovedRequirement('GreaterThan', 95)
    q2 = NumberHitsApprovedRequirement('GreaterThan', 500)
    q3 = LocaleRequirement('EqualTo', 'US')
    qualifications = Qualifications([q1, q2, q3])

    response_groups = None

    print "Submiting HITs"
    conn = mturk.get_connection()

    for n in range(n_hits):
        print "Hit #", n

        conn.create_hit(
            question=EQ, lifetime=lifetime, max_assignments=max_assignments,
            title=title, description=description, keywords=keywords, reward=reward,
            duration=duration, approval_delay=approval_delay,
            qualifications=qualifications, response_groups=response_groups)
