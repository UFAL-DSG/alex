#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""
Traverses the filesystem below a specified directory, looking for call log
directories. Writes a file containing statistics about each phone number
(extracted from the call log dirs' names):

  * number of calls
  * total size of recorded wav files
  * last expected date the caller would call
  * last date the caller actually called
  * the phone number

Call with -h to obtain the help for command line arguments.

2012-12-11
Matěj Korvas
"""

import argparse
import os.path
from copy import copy
from datetime import datetime
from glob import iglob
from math import sqrt
from os.path import basename, getsize

from SDS.utils.fs import find


epoch_start = datetime(year=1970, month=1, day=1)
infty = float('Inf')


def mean(collection):
    try:
        return sum(collection) / len(collection)
    except ZeroDivisionError:
        raise ValueError('The collection for computing mean has to be '
                         'non-empty.')
    except TypeError:
        pass
    # If adding is not an option, maybe differences can be added (such as in
    # the case of datetimes).
    coll_copy = None
    try:
        start = collection[0]
    except IndexError:
        raise ValueError('The collection for computing mean has to be '
                         'non-empty.')
    except KeyError:
        coll_copy = copy(collection)
        try:
            start = copy.pop()
        except KeyError:
            raise ValueError('The collection for computing mean has to be '
                             'non-empty.')
    # Case of indexables.
    if coll_copy is None:
        return ((start + sum(lambda elem: elem - start, collection[1:]))
                / len(collection))
    # Case of non-indexables.
    else:
        return sum(coll_copy, start=start) / len(collection)


def var(collection):
    n = len(collection)
    if n < 2:
        return infty
    sample_mean = mean(collection)
    return 1. / (n - 1) * ((1. / n) * sum(map(lambda x: x * x, collection))
                           - sample_mean * sample_mean)


def sd(collection):
    return sqrt(var(collection))


def td__total_seconds(td):
    """Total seconds in the timedelta."""
    return ((td.days * 86400 + td.seconds) * 10 ** 6 +
            td.microseconds) / 10 ** 6


def set_and_ret(indexable, idx, val):
    indexable[idx] = val
    return indexable


if __name__ == '__main__':
    # Parse arguments.
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Creates statistics of who called when, based on call log files.

      """)

    parser.add_argument('indir', action="store",
                        help='a root directory to search for call logs')
    parser.add_argument('outfile', action="store",
                        help='path towards the output file containing the '
                             'statistics')

    args = parser.parse_args()

    voip_names = find(args.indir, 'voip-*', mindepth=0, prune=True)
    # Here we assume the following format for call-log directory basenames:
    #   voip-<phone>-<YYMMDD_HHMMSS>
    voip_parts = [set_and_ret(basename(name).split('-'), 0, name)
                  for name in voip_names]
    # Here we assume the following format for call-log files:
    #   jurcic-<num>-<YYMMDD_HHMMSS>_<ms-start>_<ms-end>.wav
    # where
    #   num =~ /\d\d\d/
    #   ms-start =~ /\d{7}/
    #   ms-end =~ /\d{7}/
    #
    # ...ms-start and ms-end actually denote hundredths of seconds, not
    # milliseconds.

    # Build the mapping (phone_no -> timestamps_of_calls).
    # Build the mapping (phone_no -> total_size_of_call_logs).
    call_timestamps = dict()
    call_size = dict()
    for split in voip_parts:
        voip_path = split[0]
        phone = split[1]
        date_str = split[2]
        # Transform the date string into a timestamp.
        date = datetime(year=2000 + int(date_str[:2]),
                        month=int(date_str[2:4]),
                        day=int(date_str[4:6]),
                        hour=int(date_str[7:9]),
                        minute=int(date_str[9:11]),
                        second=int(date_str[11:13]))
        timestamp = td__total_seconds(date - epoch_start)
        # Compute the total size of the wavs.
        wavs = iglob(os.path.join(
                     voip_path,
                     'jurcic-???-??????_??????_???????_???????.wav'))
        total = 0  # total size in bytes
        for wav in wavs:
            total += getsize(wav)
        # Save the timestamp and the size.
        call_timestamps.setdefault(phone, []).append(timestamp)
        call_size[phone] = call_size.get(phone, 0) + total
    # Build the mapping (phone_no -> last_expected_call_timestamp)
    # by taking the "last expected" to be the mean plus 3 * sd.
    last_exp_timestamps = dict()
    for phone in call_timestamps:
        timestamps = call_timestamps[phone]
        last_exp_timestamps[phone] = mean(timestamps) + 3 * sd(timestamps)
    with open(args.outfile, 'w') as outfile:
        for phone, last_exp in sorted(last_exp_timestamps.items(),
                                      key=lambda item: item[1]):
            try:
                last_exp_dt = datetime.fromtimestamp(last_exp)
            except ValueError:
                last_exp_dt = datetime.max
            last_act_dt = datetime.fromtimestamp(max(call_timestamps[phone]))
            outfile.write('{num}\t{size}\t{lastexp}\t{lastact}\t{phone}\n'\
                          .format(num=len(call_timestamps[phone]),
                                  size=call_size[phone],
                                  lastexp=str(last_exp_dt),
                                  lastact=str(last_act_dt),
                                  phone=phone))
