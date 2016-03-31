#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import re
import sys


class DataLine(object):

    def __init__(self, dat=None, abstr_utt=None, abstr_da=None, utt=None, da=None, occ_num=None):
        self.dat = dat
        self.abstr_utt = abstr_utt
        self.abstr_da = abstr_da
        self.utt = utt
        self.da = da
        self.occ_num = occ_num

    def as_tuple(self, use_occ_nums=False):
        if use_occ_nums:
            return (self.dat, self.abstr_utt, self.abstr_da, self.utt, self.da, self.occ_num)
        return (self.dat, self.abstr_utt, self.abstr_da, self.utt, self.da)

    def __unicode__(self):
        return "\t".join(self.as_tuple())

    @staticmethod
    def from_csv_line(line, columns):
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
        # the type of response and the original abstr. utterance should be enough to distinguish
        return self.abstr_utt + "|" + self.abstr_da + "|" + self.dat

    @property
    def slots(self):
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
        slots = re.sub('=[^,;]*', '', self.da)
        slots = re.sub('(; )?[a-z]: ', '', slots)
        slots = re.sub(' +', ' ', slots)
        slots = slots.strip()
        return slots.split(' ')

    @property
    def values_list(self):
        """Returns a list of concrete slot values (skipping '?')."""
        return [val[1:] for val in re.findall('=[^,;]*', self.da) if val[1:] != '?']

    @property
    def slot_values(self):
        """Returns a slot -> value dictionary; only for slots that have concrete values."""
        ret = {}
        for match in re.finditer('([a-z_]+)=([^,;]*)', self.da):
            if match.group(2) == '?':  # skip slots without values
                continue
            ret[match.group(1)] = match.group(2)
        return ret

    @staticmethod
    def get_columns_from_header(header):
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
        if use_occ_nums:
            return ('type', 'abstr_utt', 'abstr_da', 'utt', 'da', 'occ_num')
        return ('type', 'abstr_utt', 'abstr_da', 'utt', 'da')


class Result(object):

    def __init__(self, data, headers):

        self.__headers = headers
        for attr, val in zip(headers, data):
            setattr(self, attr, val)

    def as_array(self):

        ret = []
        for attr in self.__headers:
            ret.append(getattr(self, attr, ''))
        return ret


# following from Python cookbook, #475186
def has_colours(stream):
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
    if stdout_has_colours:
        seq = "\x1b[1;%dm" % (30+colour) + text + "\x1b[0m"
        sys.stdout.write(seq)
    else:
        sys.stdout.write(text)
