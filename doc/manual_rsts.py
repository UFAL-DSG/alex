#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

import glob
import os.path
import shutil

root = '..'

def get_all_rsts(root='.'):
    f = []
    f.extend(glob.glob(os.path.join(root, '*.rst')))
    f.extend(glob.glob(os.path.join(root,'alex', '*.rst')))
    f.extend(glob.glob(os.path.join(root,'alex', '*', '*.rst')))
    f.extend(glob.glob(os.path.join(root,'alex', '*', '*', '*.rst')))
    f.extend(glob.glob(os.path.join(root,'alex', '*', '*', '*', '*.rst')))
    f.extend(glob.glob(os.path.join(root,'alex', '*', '*', '*', '*', '*.rst')))
    f.extend(glob.glob(os.path.join(root,'alex', '*', '*', '*', '*', '*', '*.rst')))
    # f.extend(glob.glob(os.path.join(root,'alex', '*', '*', '*', '*', '*', '*', '*.rst')))
    # f.extend(glob.glob(os.path.join(root,'alex', '*', '*', '*', '*', '*', '*', '*', '*.rst')))
    # f.extend(glob.glob(os.path.join(root,'alex', '*', '*', '*', '*', '*', '*', '*', '*', '*.rst'))

    f.sort()

    for i in f:
        shutil.copy2(i, os.path.join('_man_rst',i.replace('/','.').replace('...','')))

    return f

rsts = get_all_rsts(root)

with open(os.path.join('_man_rst','index.rst'), 'w') as f:
    f.write('Index of manually written in source code tree documentation\n')
    f.write('===========================================================\n')
    f.write('.. toctree::\n')
    f.write('   :maxdepth: 2\n')
    f.write('   \n')
    for i in rsts:
        if 'alex' in i:
            f.write('   %s\n' % i.replace('/','.').replace('...','').replace('.rst',''))

