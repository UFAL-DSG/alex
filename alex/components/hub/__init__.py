#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os.path

from alex import AlexException


class VoipIOException(AlexException):
    pass

from .hub import Hub


# Add the directory containing the alex package to python path
# FIXME by Oplatek: are we not using autopath? Do we really need this?
path, directory = os.path.split(os.path.abspath(__file__))
while directory and directory != 'alex':
    path, directory = os.path.split(path)
if directory == 'alex':
    sys.path.append(path)
