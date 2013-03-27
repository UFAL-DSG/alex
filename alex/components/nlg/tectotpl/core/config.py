#!/usr/bin/env python
# coding=utf-8
#
# Configuration save / load
#
from __future__ import unicode_literals
import yaml
import os


config_data = {
               'data_dir': '~/.treex-py/data/'  # resource data directory
               }
try:
    f = open(os.path.expanduser(os.path.normpath('~/.treex-py/config.yaml')))
    config_data = yaml.load(f)
    f.close()
except:
    pass


def data_dir():
    "Return the reource data directory"
    path = os.path.normpath(config_data['data_dir'])
    if path.startswith('~'):
        path = os.path.expanduser(path)
    return path

# TODO save configuration at exit (atexit.register)
