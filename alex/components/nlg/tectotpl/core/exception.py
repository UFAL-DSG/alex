#!/usr/bin/env python
# coding=utf-8
#
# Classes related to Treex exceptions
#
from __future__ import unicode_literals
__author__ = "Ondřej Dušek"
__date__ = "2012"


class TreexException(Exception):
    "Common ancestor for Treex exception"

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'TREEX-FATAL: ' + self.__class__.__name__ + ': ' + self.message


class ScenarioException(TreexException):
    "Scenario-related exception."

    def __init__(self, text):
        TreexException.__init__(self, text)


class LoadingException(TreexException):
    "Block loading exception"

    def __init__(self, text):
        TreexException.__init__(self, text)


class RuntimeException(TreexException):
    "Block runtime exception"

    def __init__(self, text):
        TreexException.__init__(self, text)


class DataException(TreexException):
    "Data file not found exception"

    def __init__(self, path):
        TreexException.__init__(self, 'Cannot find file in the data directory:'
                                + path)
