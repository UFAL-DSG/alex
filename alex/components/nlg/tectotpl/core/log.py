#!/usr/bin/env python
# coding=utf-8
from __future__ import unicode_literals

__author__ = "Ondřej Dušek"
__date__ = "2012"

import sys
import codecs
from logging import basicConfig, info, warn, INFO


# configure logging
LOGFORMAT = '%(asctime)-15s %(message)s'
basicConfig(format=LOGFORMAT, stream=codecs.getwriter('utf-8')(sys.stderr),
            level=INFO)


def log_info(message):
    "Print an information message"
    info('TECTOTPL-INFO: ' + message)


def log_warn(message):
    "Print a warning message"
    warn('TECTOTPL-WARN: ' + message)
