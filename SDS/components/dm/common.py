#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.

from SDS.utils.exception import SemHubException

from .dummydialoguemanager import DummyDM
from .ufalruledm import UfalRuleDM


def dm_factory(dm_type, cfg):
    dm = None

    # do not forget to maintain all supported dialogue managers
    if dm_type == 'Dummy':
        dm = DummyDM(cfg)
    elif dm_type == 'UfalRuleDM':
        dm = UfalRuleDM(cfg)
    else:
        raise SemHubException(
            'Unsupported dialogue manager: %s' % dm_type)

    return dm


def get_dm_type(cfg):
    return cfg['DM']['type']
