#!/usr/bin/env python
# coding=utf-8
#
# Small utility functions
#

from __future__ import unicode_literals
import codecs
import gzip
from io import IOBase
from codecs import StreamReader, StreamWriter

__author__ = "Ondřej Dušek"
__date__ = "2012"


def first(condition_function, sequence, default=None):
    """\
    Return first item in sequence where condition_function(item) == True,
    or None if no such item exists.
    """
    for item in sequence:
        if condition_function(item):
            return item
    return default


def as_list(value):
    """\
    Cast anything to a list (just copy a list or a tuple,
    or put an atomic item to as a single element to a list).
    """
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def file_stream(filename, mode='r', encoding='UTF-8'):
    """\
    Given a file stream or a file name, return the corresponding stream,
    handling GZip. Depending on mode, open an input or output stream.
    """
    # open file
    if isinstance(filename, (file, IOBase, StreamReader, StreamWriter)):
        fh = filename
    elif filename.endswith('.gz'):
        fh = gzip.open(filename, mode)
    else:
        fh = open(filename, mode)
    # support encodings
    if encoding is not None:
        if mode.startswith('r'):
            fh = codecs.getreader(encoding)(fh)
        else:
            fh = codecs.getwriter(encoding)(fh)
    return fh
