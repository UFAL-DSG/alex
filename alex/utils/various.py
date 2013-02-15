#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set fdm=marker :
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
#
# pylint: disable-msg=E1101

from collections import defaultdict


def split_to_bins(A, S=4):
    """Split the A array into bins of size N."""
    m, n = divmod(len(A), S)
    return [A[i * S:(i + 1) * S] for i in range(m + bool(n))]


def flatten(list_, ltypes=(list, tuple)):
    """Flatten nested list into a simple list."""
#{{{
    # Coerce the input sequence into a list for this function.
    ltype = type(list_)
    list_ = list(list_)
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
            else: # if the list-like element is non-empty,
                # Catenate its elements to the main list at the current
                # position.
                list_[i:i + 1] = list_[i]
        i += 1
    # Coerce the main list into the original type and return.
    return ltype(list_)
#}}}


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


class ComparisonByClassFields(object):
    """A mixin class that causes its instantiations to be compared equal iff
    their member fields compare equal. (Precisely, if their .__dict__ compare
    equal.)

    """

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
