#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import os.path
import time
import shutil

from glob import glob

if __name__ == '__main__':
    new_dir = 'VYSTADIAL-RAM'
    new_dir += '-' + datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")

    os.mkdir(new_dir)


    pcm_files = glob('call_logs/*/all-*.recorded.wav')

    for f in sorted(pcm_files):

        size = os.stat(f).st_size

        if size > 1000000:
            # process only files with 2 minutes of audio or longer
            new_f_name = os.path.join(new_dir, os.path.basename(f))

            print 'Copying: ', f, ' to ', new_f_name

            # channel A
            shutil.copy2(f, new_f_name)

        else:
            print '# Ignoring: ', f
