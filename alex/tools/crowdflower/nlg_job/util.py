#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Helper objects and routines for the construction of Alex Context NLG Dataset."""

from __future__ import unicode_literals
import re
import sys


class DataLine(object):
    """This holds one line of the NLG response task assignments for CF users. It has the following
    fields:

        dat = response dialogue act type (reply, apologize, confirm, request; as used in the CF
                task, will be later converted to inform, inform_no_match, iconfirm, request).
        abstr_utt = context user utterance (abstracted, original)
        abstr_da = original SLU parse (abstracted)
        utt = context user utterance (with filled in lexical values)
        da = response DA -- source slots and values (DA type is stored in dat field)
        occ_num = number of occurences of the context utterance in the recorded calls
    """

    def __init__(self, dat=None, abstr_utt=None, abstr_da=None, utt=None, da=None, occ_num=None):
        """Constructor, default values may be provided (otherwise None)"""
        self.dat = dat
        self.abstr_utt = abstr_utt
        self.abstr_da = abstr_da
        self.utt = utt
        self.da = da
        self.occ_num = occ_num

    def as_tuple(self, use_occ_nums=False):
        """Return the DataLine as a tuple, with or without its context occurrence count."""
        if use_occ_nums:
            return (self.dat, self.abstr_utt, self.abstr_da, self.utt, self.da, self.occ_num)
        return (self.dat, self.abstr_utt, self.abstr_da, self.utt, self.da)

    def __unicode__(self):
        return "\t".join(self.as_tuple())

    @staticmethod
    def from_csv_line(line, columns):
        """Construct a new DataLine and fill in values from a CSV file line.

        @param line: an array as read by Python's CSV module
        @param columns: column indexes found in header -- a dict with field names as keys and
            indexes as values (use get_columns_from_header() to obtain it)
        """
        ret = DataLine()
        ret.dat = line[columns['dat']]
        ret.abstr_utt = line[columns['abstr_utt']]
        ret.abstr_da = line[columns['abstr_da']]
        ret.utt = line[columns['utt']]
        ret.da = line[columns['da']]
        if 'occ_num' in columns:
            ret.occ_num = line[columns['occ_num']]
        return ret

    @property
    def signature(self):
        """DataLine "signature" (unique ID), consisting of the context utterance and SLU parse +
        response type.
        """
        # the type of response and the original abstr. utterance should be enough to distinguish
        return self.abstr_utt + "|" + self.abstr_da + "|" + self.dat

    @property
    def slots(self):
        """Return all slots that occur in the response DA in this DataLine (as a string)"""
        parts = re.sub('=[^,;]*', '', self.da)
        parts = parts.split('; ')
        slots = ''
        for part in parts:
            if ':' in part:
                ptype, part = part.split(': ')
                slots += ptype + ':'
            slots += ','.join(sorted(part.split(', ')))
            slots += ' '
        return slots

    @property
    def slots_list(self):
        """Return all slots that occur in the response DA in this DataLine *with a concrete value*
        (as a list). Ignore slots whose values should be requested."""
        slots = re.sub('=[^,;]*', '', self.da)
        slots = re.sub('(; )?[a-z]: ', '', slots)
        slots = re.sub(' +', ' ', slots)
        slots = slots.strip()
        return slots.split(' ')

    @property
    def values_list(self):
        """Return a list of concrete slot values occurring in the response DA in this DataLine
        (skipping all '?'s)."""
        return [val[1:] for val in re.findall('=[^,;]*', self.da) if val[1:] != '?']

    @property
    def slot_values(self):
        """Return a slot -> value dictionary for slots and values in the response DA of this
        DataLine; only for slots that have concrete values (skipping all '?'s)."""
        ret = {}
        for match in re.finditer('([a-z_]+)=([^,;]*)', self.da):
            if match.group(2) == '?':  # skip slots without values
                continue
            ret[match.group(1)] = match.group(2)
        return ret

    @staticmethod
    def get_columns_from_header(header):
        """Given a header read from a CSV file, find indexes of all required columns and return
        them in a dict to be used by from_csv_line()."""
        columns = {'dat': header.index('type'),
                   'abstr_utt': header.index('abstr_utt'),
                   'abstr_da': header.index('abstr_da'),
                   'utt': header.index('utt'),
                   'da': header.index('da')}
        if 'occ_num' in header:
            columns['occ_num'] = header.index('occ_num')
        return columns

    @staticmethod
    def get_headers(use_occ_nums=False):
        """Return headers to be written into an output CSV file which will contain DataLines."""
        if use_occ_nums:
            return ('type', 'abstr_utt', 'abstr_da', 'utt', 'da', 'occ_num')
        return ('type', 'abstr_utt', 'abstr_da', 'utt', 'da')


class Result(object):
    """This holds a general CSV line, with all CSV fields as attributes of the object."""

    def __init__(self, data, headers):
        """Initialize, storing the given CSV headers and initializing using the given data
        (in the same order as the headers).

        @param data: a list of data fields, a line as read by Python CSV module
        @param headers: a list of corresponding field names, e.g., CSV header as read by Python \
            CSV module
        """
        self.__headers = headers
        for attr, val in zip(headers, data):
            setattr(self, attr, val)

    def as_array(self):
        """Return the values as an array, in the order given by the current headers (which were
        provided upon object construction)."""
        ret = []
        for attr in self.__headers:
            ret.append(getattr(self, attr, ''))
        return ret

    def as_dict(self):
        """Return the values as a dictionary, with keys for field names and values for the
        corresponding values."""
        ret = {}
        for attr in self.__headers:
            ret[attr] = getattr(self, attr, '')
        return ret


# following from Python cookbook, #475186
def has_colours(stream):
    """Detect if the given output stream supports color codes."""
    if not hasattr(stream, "isatty"):
        return False
    if not stream.isatty():
        return False  # auto color only on TTYs
    try:
        import curses
        curses.setupterm()
        return curses.tigetnum("colors") > 2
    except:
        # guess false in case of error
        return False


stdout_has_colours = has_colours(sys.stdout)


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


def printout(text, colour=WHITE):
    """Print text to sys.stdout using colors."""
    if stdout_has_colours:
        seq = "\x1b[1;%dm" % (30+colour) + text + "\x1b[0m"
        sys.stdout.write(seq)
    else:
        sys.stdout.write(text)
