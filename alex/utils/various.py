#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
#
# pylint: disable-msg=E1101

from collections import defaultdict
import math
import sys


def split_to_bins(A, S=4):
    """Split the A array into bins of size N."""
    m, n = divmod(len(A), S)
    return [A[i * S:(i + 1) * S] for i in range(m + bool(n))]


def flatten(list_, ltypes=(list, tuple)):
    """Flatten nested list into a simple list."""
    # Iterate `list_' from the beginning.
    i = 0
    while i < len(list_):
        # While the list_'s i-th element is of a list-like type,
        while isinstance(list_[i], ltypes):
            # If the list-like element is empty,
            if not list_[i]:
                # Remove the empty element.
                list_.pop(i)
                i -= 1
                break
            else:  # if the list-like element is non-empty,
                # Catenate its elements to the main list at the current
                # position.
                list_[i:i + 1] = list_[i]
        i += 1
    # Coerce the main list into the original type and return.
    return list_


def get_text_from_xml_node(node):
    """ Get text from all child nodes and concatenate it.
    """
    rc = []
    for cn in node.childNodes:
        if cn.nodeType == cn.TEXT_NODE:
            rc.append(cn.data)
    return ''.join(rc).strip()


class nesteddict(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, nesteddict)

    def walk(self):
        for key, value in self.iteritems():
            if isinstance(value, nesteddict):
                for tup in value.walk():
                    yield (key,) + tup
                else:
                    yield key, value


def crop_to_finite(val):
    if math.isinf(val):
        if isinstance(val, int):
            ret = sys.maxint
        else:
            ret = sys.float_info.max
        return (-1 + 2 * (val > 0)) * ret
    return val


def group_by(objects, attrs):
    """Groups `objects' by the values of their attributes `attrs'.

    Returns a dictionary mapping from a tuple of attribute values to a list of
    objects with those attribute values.

    """
    groups = dict()
    for obj in objects:
        key = tuple(getattr(obj, attr) for attr in attrs)
        groups.setdefault(key, []).append(obj)
    return groups


def remove_dups_stable(l):
    """Remove duplicates from a list but keep the ordering.

    @return: Iterator over unique values in the list
    """
    seen = set()
    for i in l:
        if i not in seen:
            yield i
            seen.add(i)
