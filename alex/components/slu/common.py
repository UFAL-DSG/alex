#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fileencoding=UTF-8 :

from __future__ import unicode_literals

import inspect
from alex.components.slu.base import CategoryLabelDatabase, SLUInterface
from alex.components.slu.exceptions import SLUException
from alex.components.slu.dailrclassifier import DAILogRegClassifier

def get_slu_type(cfg):
    """
    Reads the SLU type from the configuration.
    """
    return cfg['SLU']['type']

def slu_factory(cfg, slu_type=None):
    """
    Creates an SLU parser.

    :param cfg:
    :param slu_type:
    :param require_model:
    :param training:
    :param verbose:

    """

    #This new and simple factory code.
    if slu_type is None:
        slu_type = get_slu_type(cfg)

    if inspect.isclass(slu_type) and issubclass(slu_type, DAILogRegClassifier):
        cldb = CategoryLabelDatabase(cfg['SLU'][slu_type]['cldb_fname'])
        preprocessing = cfg['SLU'][slu_type]['preprocessing_cls'](cldb)
        slu = slu_type(cldb, preprocessing)
        slu.load_model(cfg['SLU'][slu_type]['model_fname'])
        return slu
    elif inspect.isclass(slu_type) and issubclass(slu_type, SLUInterface):
        cldb = CategoryLabelDatabase(cfg['SLU'][slu_type]['cldb_fname'])
        preprocessing = cfg['SLU'][slu_type]['preprocessing_cls'](cldb)
        slu = slu_type(preprocessing, cfg)
        return slu

    raise SLUException('Unsupported SLU parser: %s' % slu_type)
