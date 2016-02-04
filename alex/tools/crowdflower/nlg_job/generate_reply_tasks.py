#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
Generate reply/confirm CrowdFlower tasks for the PTIEN domain.

Usage: ./generate_reply_tasks.py [--filter-threshold N] input.tsv > output.tsv
"""

# TODO: Filter inputs that are just composed of slot values


from __future__ import unicode_literals
from alex.components.slu.da import DialogueAct, DialogueActItem

from argparse import ArgumentParser
import codecs
import re
import sys
import random
import csv

# Start IPdb on error in interactive mode
from tgen.debug import exc_info_hook
sys.excepthook = exc_info_hook


STOPS = ['Astor Place',
         'Bleecker Street',
         'Bowery',
         'Bowling Green',
         'Broad Street',
         'Bryant Park',
         'Canal Street',
         'Cathedral Parkway',
         'Central Park',
         'Chambers Street',
         # 'City College',
         'City Hall',
         'Columbia University',
         'Columbus Circle',
         'Cortlandt Street',
         'Delancey Street',
         'Dyckman Street',
         'East Broadway',
         'Essex Street',
         'Franklin Street',
         'Fulton Street',
         'Grand Central',
         'Grand Street',
         # 'Harlem',
         'Herald Square',
         'Houston Street',
         # 'Hudson Yards',
         # 'Hunter College',
         'Inwood',
         # 'Lafayette Street',
         'Lincoln Center',
         'Marble Hill',
         # 'Museum of Natural History',
         # 'New York University',
         'Park Place',
         'Penn Station',
         'Port Authority Bus Terminal',
         'Prince Street',
         'Rector Street',
         'Rockefeller Center',
         'Roosevelt Island',
         # 'Sheridan Square',
         # 'South Ferry',
         # 'Spring Street',
         'Times Square',
         'Union Square',
         'Wall Street',
         'Washington Square',
         'World Trade Center', ]

WORD_FOR_NUMBER = ['zero', 'one', 'two', 'three', 'four', 'five', 'six',
                   'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']

BUS_LINES = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 14, 15, 20, 21, 22, 23, 31,
             34, 35, 42, 50, 57, 60, 66, 72, 79, 86, 96, 98, 100, 101, 102,
             103, 104, 106, 116]

NO_CONNECTION_PROB = 0.1


def word_for_ampm(hour, ampm):
    """Return 'morning', 'afternoon', or 'evening' for the given hour and
    AM/PM setting.
    """
    if ampm == 'am':
        return 'morning'
    if hour < 6:
        return 'afternoon'
    return 'evening'

def deabstract(utt, dais):
    """De-abstract an utterance and a list of corresponding DAIs, so that
    a specific answer is provided.
    """
    # prepare some data to be used
    from_stop, to_stop = random.sample(STOPS, 2)
    time = random.choice(range(7,23))
    ampm = 'am' if time < 12 else 'pm'
    time %= 12
    vehicle = random.choice(['subway', 'bus'])

    dais_out = []  # create a completely new structure, so that we keep the abstract original

    # process DAIs and deabstract them, along with the utterance
    for dai in dais:

        dai_out = DialogueActItem(dai.dat, dai.name, dai.value)
        dais_out.append(dai_out)

        if dai.name == 'from_stop':
            dai_out.value = from_stop
            utt_r = re.sub(r'(from |^)\*STOP', r'\1%s' % from_stop, utt)
        elif dai.name == 'to_stop':
            dai_out.value = to_stop
            utt_r = re.sub(r'(destination is|arrive (in|at)|to|towards?|for|into) \*STOP',
                           r'\1 %s' % to_stop, utt)
        elif dai.name == 'vehicle':
            dai_out.value = vehicle
            utt_r = re.sub(r'\*VEHICLE', vehicle, utt)
        elif 'time' in dai.name and dai.dat == 'inform':
            dai_out.value = unicode(time) + ':00'
            utt_r = re.sub(r'\*NUMBER', WORD_FOR_NUMBER[time], utt)
        elif 'ampm' in dai.name:
            dai_out.value = ampm
            utt_r = re.sub(r'(in the) \*AMPM', r'\1 %s' % word_for_ampm(time, ampm), utt)
            utt_r = re.sub(r'\*AMPM', ampm, utt_r)
        elif dai.value is None or '*' not in dai.value or dai.dat != 'inform':
            continue  # some things do not need deabstracting
        else:
            raise NotImplementedError('Cannot deabstract slot: ' + dai.name + " -- " + utt)

        if utt_r == utt:
            raise NotImplementedError('Cannot replace slot: ' + dai.name + " -- " + utt + " / " + unicode(dais))

        utt = utt_r

    return utt, dais_out

def normalize_utterance(utt):
    """Normalize utterance (remove double streets, convert streets to stops)."""

    # TODO handle boroughs ??
    utt = re.sub(r'\*STREET and \*STREET', r'*STREET', utt)
    utt = re.sub(r'\*STREET', r'*STOP', utt)
    return utt


def normalize_da(da):
    """Normalize DA to contain only things that we would like to confirm or reply to."""

    # keep just request/inform, remove 2nd streets, remove boroughs
    dais = [dai for dai in da.dais
            if (dai.dat in ['request', 'inform'] and
                dai.name not in ['borough', 'to_street2', 'from_street2', 'task'])]

    # convert streets to stops
    for dai in dais:
        dai.name = re.sub('_street$', '_stop', dai.name)

    return dais


def generate_confirm(utt, dais):
    """Generate a confirmation task for the given utterance and DAIs list."""

    ret = ['confirm', utt, '&'.join([unicode(dai) for dai in dais])]

    utt, dais = deabstract(utt, [dai for dai in dais
                                 if re.match('^(from|to|departure_time|arrival_time|ampm|vehicle)',
                                             dai.name)])
    dais_str = ', '.join([dai.name + '=' + dai.value for dai in dais])

    return ret + [utt, dais_str]

def generate_reply(utt, dais):
    """Generate a reply task for the given utterance and DAIs list."""

    ret = ['reply', utt, '&'.join([unicode(dai) for dai in dais])]

    utt, dais = deabstract(utt, dais)

    # offer a ride (meeting the specifications in dais)
    if all([dai.dat == 'inform' for dai in dais]):

        if random.random() < NO_CONNECTION_PROB:
            info = {'line': 'not found'}
            # TODO maybe want to display the criteria used for searching without results
        else:
            info = {dai.name: dai.value for dai in dais}
            if 'vehicle' not in info:
                info['vehicle'] = random.choice(['subway', 'bus'])
            if info['vehicle'] == 'subway':
                info['line'] = random.choice('1234567ABCDEFGJLMNQRZ')
            else:
                info['line'] = 'M' + str(random.choice(BUS_LINES))
            if 'ampm' not in info:
                if 'time' in info:
                    time_val, _ = info['time'].split(':')
                    time_val = int(time_val)
                    if time_val < 7 or time_val == 12:
                        info['ampm'] = 'pm'
                if 'ampm' not in info:
                    info['ampm'] = random.choice(['am', 'pm'])
            if 'departure_time' not in info:
                if info['ampm'] == 'am':
                    info['departure_time'] = str(random.choice(range(7, 12))) + ':00'
                else:
                    info['departure_time'] = str(random.choice(range(1, 13))) + ':00'
            if 'from_stop' not in info:
                info['from_stop'] = random.choice(STOPS)
            if 'to_stop' not in info:
                remaining_stops = list(STOPS)
                remaining_stops.remove(info['from_stop'])
                info['to_stop'] = random.choice(remaining_stops)

            info['direction'] = info['to_stop']
            del info['to_stop']

            info['departure_time'] = re.sub(r'00$', '%02d' % random.choice(range(20)),
                                            info['departure_time'])
            info['departure_time'] += info['ampm']
            del info['ampm']

        dais_str = [slot + '=' + value for slot, value in info.iteritems()]
        random.shuffle(dais_str)
        dais_str = ', '.join(dais_str)

    # offer additional information
    else:
        dais_str = ''
        if any([dai.name == 'distance' for dai in dais]):
            dais_str += ', distance=%3.1f' % (random.random() * 12)
        if any([dai.name == 'num_transfers' for dai in dais]):
            dais_str += ', num_transfers=%d' % random.choice(range(0, 2))
        if any([dai.name == 'duration' for dai in dais]):
            dais_str += ', duration=%d min' % random.choice(range(10,80))
        if any([dai.name == 'arrival_time' for dai in dais]):
            hr = random.choice(range(7,23))
            ampm = 'am' if hr < 12 else 'pm'
            hr %= 12
            min = random.choice(range(60))
            dais_str += ', arrival_time=%d:%d%s' % (hr, min, ampm)

        if dais_str == '':
            raise NotImplementedError('Cannot generate a reply for: ' + unicode(dais))

        dais_str = dais_str[2:]

    return ret + [utt, dais_str]


def process_utt(utt, da):
    """Process a single utterance + DA pair, generating corresponding tasks if applicable."""

    utt = normalize_utterance(utt)
    dais = normalize_da(da)

    ret = []

    if not dais:  # skip things that did not contain anything to reply/confirm
        return ret

    # check if we should generate a confirmation task, and do it
    if any([dai.dat == 'inform' and
            re.match('^(from|to|departure_time|arrival_time|vehicle)', dai.name)
            for dai in dais]):
        ret.append(generate_confirm(utt, dais))

    # generate a reply task
    ret.append(generate_reply(utt, dais))

    return ret

def main(input_file, filter_threshold):

    data = [['type', 'abstr_utt', 'abstr_da', 'utt', 'da']]  # create output headers

    with codecs.open(input_file, "r", 'UTF-8') as fh:
        for line in fh:
            print >> sys.stderr, 'Processing: ', line.strip()
            occ_num, utt, da = line.strip().split('\t')
            da = DialogueAct(da_str=da)
            occ_num = int(occ_num)

            if occ_num < filter_threshold:
                print >> sys.stderr, 'Input "%s" has only %d occurrences, skipping' % (utt, occ_num)
                continue

            if re.match(r'^(\*[A-Z_]+)(\s+\*[A-Z_]+)*$', utt):
                print >> sys.stderr, 'Input "%s" only contains slots, skipping' % utt
                continue

            try:
                ret = process_utt(utt, da)
                print >> sys.stderr, 'Result:', "\n".join(["\t".join(i) for i in ret])
                print >> sys.stderr, ''
                data.extend(ret)
            except NotImplementedError as e:
                print >> sys.stderr, 'Error:', e

    with codecs.getwriter('utf-8')(sys.stdout) as fh:
        csvwrite = csv.writer(fh, delimiter=b"\t")
        for line in data:
            csvwrite.writerow(line)


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('-f', '--filter-threshold', type=int, default=1)
    ap.add_argument('input_file')
    random.seed(0)
    args = ap.parse_args()
    main(input_file=args.input_file, filter_threshold=args.filter_threshold)

