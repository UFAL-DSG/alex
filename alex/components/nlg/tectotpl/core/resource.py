#!/usr/bin/env python
# coding=utf-8
#
# Requiring files from the data directory
#
from __future__ import unicode_literals
import os
import treex.core.config
from treex.core.exception import DataException


def get_data(path):
    "Return a true path to a data file in the data directory"
    data_dir = treex.core.config.data_dir()
    result_path = os.path.normpath(data_dir + '/' + path)
    if os.path.isfile(result_path):
        return result_path
    else:
        raise DataException(path)
