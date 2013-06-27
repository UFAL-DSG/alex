#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# from alex.components.slu.base import *
#
# __all__ = ['da', 'dailrclassifier', 'daiklrclassifier', 'templateclassifier']

from alex import AlexException


class SLUException(AlexException):
    pass


class DAILRException(SLUException):
    pass


class CuedDialogActError(SLUException):
    pass
