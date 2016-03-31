#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Checking CrowdFlower results in an interactive script.

The script will present the individual CF users' creations and your task is to accept them (Y)
or reject them (N). You may further include an entrainment assessment (L/S/LS) and/or a post-edit
of the sentence (separated by two spaces, or one if entrainment assesment is present).
"""

from __future__ import unicode_literals
from argparse import ArgumentParser, FileType
import sys
import unicodecsv as csv
import re
from util import *


def main(args):

    results = []
    headers = None
    input_lines = []
    input_sigs = set()
    skipped = 0

    # load input data
    with args.input_file as fh:
        csvread = csv.reader(fh, delimiter=str(args.input_csv_delim),
                             quotechar=b'"', encoding="UTF-8")
        columns = DataLine.get_columns_from_header(csvread.next())
        for row in csvread:
            iline = DataLine.from_csv_line(row, columns)
            input_lines.append(iline)
            input_sigs.add(iline.signature)

    # load all results files provided
    for results_file in args.results_files:
        with results_file as fh:

            print >> sys.stderr, 'Processing ' + results_file.name + '...'

            csvread = csv.reader(fh, delimiter=str(args.results_csv_delim),
                                 quotechar=b'"', encoding="UTF-8")
            if headers is None:
                headers = csvread.next()
            else:
                cur_headers = csvread.next()
                # check headers, but ignore the last column ("check_result")
                if headers != cur_headers and (headers[-1] != 'check_result' or headers[:-1] != cur_headers):
                    raise ValueError('Incompatible headers in ' + results_file.name)

            columns = DataLine.get_columns_from_header(headers)
            for row in csvread:
                # keep track of how many judgments are finished in the results
                dl = DataLine.from_csv_line(row, columns)
                if dl.signature in input_sigs:
                    row = Result(row, headers)
                    results.append(row)
                else:
                    skipped += 1

    if 'check_result' not in headers:
        headers.append('check_result')

    print >> sys.stderr, "Loaded %d results, skipped %d." % (len(results), skipped)

    # work on them -- main loop
    cur_pos = 0
    status = ''
    while cur_pos < len(results):
        row = results[cur_pos]

        if status not in ['b', 'm'] and getattr(row, 'check_result', ''):  # move over already finished ones
            cur_pos += 1
            continue

        print ''
        printout("[%d]\n" % cur_pos, RED)
        printout(row.utt + "\n", YELLOW)
        print row.type, row.da
        printout(row.reply + "\n", GREEN)

        if args.command_file is not None:
            raw_result = args.command_file.readline()
            raw_result = raw_result.rstrip()
            raw_result += '  '
        else:
            raw_result = raw_input('[Q]uit/[B]ack/[Y]es/[N]o/[E]dit Entr.[S]truct/[L]/- (text of post-edit)') + '  '
        status, entrainment, postedit = raw_result.split(' ', 2)
        status = status.lower()
        entrainment = entrainment.lower()

        if status == 'b':  # go back
            cur_pos -= 1
            continue
        elif status == 'm':  # move to the specified position
            cur_pos = int(entrainment)
            continue
        elif status == 'q':  # quit
            break
        elif status == 'y':  # OK
            check_result = 'Y'
            # if marked as OK but postedit found: change status to postedit
            if postedit.strip():
                print 'STATUS CHANGED TO e'
                status = 'e'
                check_result = 'E'
            # frequent error -- normalize (TODO move to build_dataset)
            elif ' dir ' in row.reply:
                postedit = re.sub(r'\bdir\b', 'direction', row.reply)
                print 'SUBSTITUTED "dir"'
                status = 'e'
                check_result = 'E'
            # frequent error -- normalize (TODO move to build_dataset)
            elif re.search(r'\b(could|can|did)( ?not|n\'t) found', row.reply):
                print 'SUBSTITUTED "found"'
                postedit = re.sub(r'\bfound\b', 'find', row.reply)
                status = 'e'
                check_result = 'E'

        elif status == 'n':
            check_result = 'N'
        elif status == 'e':
            check_result = 'E'
        else:
            print 'INVALID OPERATION -- ignoring'
            continue  # stay at the same position

        check_result += '-' + entrainment.upper()
        if status == 'e':
            check_result += ' ' + row.reply
            row.reply = postedit

        row.check_result = check_result
        cur_pos += 1

    print >> sys.stderr, "Writing output..."

    # save the result into the output file
    with open(args.output_file, 'w') as fh:
        # starting with the header
        csvwrite = csv.writer(fh, delimiter=str(args.output_csv_delim), lineterminator="\n",
                              quotechar=b'"', encoding="UTF-8")
        csvwrite.writerow(headers)
        for row in results:
            csvwrite.writerow(row.as_array())

        print >> sys.stderr, "Wrote %d results" % len(results)


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('-r', '--results-csv-delim', type=str, default=",")
    ap.add_argument('-i', '--input-csv-delim', type=str, default="\t")
    ap.add_argument('-o', '--output-csv-delim', type=str, default=",")
    ap.add_argument('-f', '--command-file', type=FileType('r'), default=None)
    ap.add_argument('input_file', type=FileType('r'))
    ap.add_argument('output_file', type=str)  # avoid overwriting the output straight away
    ap.add_argument('results_files', type=FileType('r'), nargs='+')
    args = ap.parse_args()
    main(args)
