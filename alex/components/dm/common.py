#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.

from alex.components.dm import DialogueManager
from alex.components.dm.ruledm.ufalruledm import UfalRuleDM
from alex.components.dm.ruledm.ufalruledm import PUfalRuleDM
from alex.components.dm.exceptions import DMException

def get_dm_type(cfg):
    return cfg['DM']['type']

def dm_factory(dm_type, cfg):
    dm = None

    # do not forget to maintain all supported dialogue managers
    if dm_type == 'basic':
        dm = DialogueManager(cfg)
    elif dm_type == 'UfalRuleDM':
        dm = UfalRuleDM(cfg)
    elif dm_type == 'PUfalRuleDM':
        dm = PUfalRuleDM(cfg)
    else:
        try:
            dm = dm_type(cfg)
        except NameError:
            raise DMException(
            'Unsupported dialogue manager: %s' % dm_type)

    return dm
