#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from alex.utils.exception import SemHubException

from .template import TemplateNLG, TectoTemplateNLG

def get_nlg_type(cfg):
    return cfg['NLG']['type']

def nlg_factory(nlg_type, cfg):
    nlg = None

    # do not forget to maintain all supported dialogue managers
    if nlg_type == 'Template':
        nlg = TemplateNLG(cfg)
    elif nlg_type == 'TectoTemplate':
        nlg = TectoTemplateNLG(cfg)
    else:
        try:
            nlg = nlg_type(cfg)
        except NameError:
            raise SemHubException('Unsupported NLG: %s' % nlg_type)

    return nlg

