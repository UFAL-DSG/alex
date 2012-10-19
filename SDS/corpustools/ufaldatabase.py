#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path

def save_database(odir, slots):
    s = 'database = {'
    for slt in sorted(slots):
        if not slt:
            continue
        s += '\n'
        s += '  "'+slt+'": {'
        s += '\n'

        for vlu in sorted(slots[slt]):
            if not vlu:
                continue
            s += '    "'+vlu+'": [' + '"'+vlu+'",],'
            s += '\n'

        s += '  },'
        s += '\n'
    s += '}'
    s += '\n'

    fo = open(os.path.join(odir,'auto_database.py'), 'w+')
    fo.write(s)
    fo.close()
