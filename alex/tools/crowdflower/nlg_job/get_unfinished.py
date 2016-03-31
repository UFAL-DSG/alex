#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
Filter rows for the NLG CrowdFlower tasks, removing the finished lines.
"""


from __future__ import unicode_literals

from argparse import ArgumentParser, FileType
import sys
import unicodecsv as csv
from collections import defaultdict

from util import *

# Start IPdb on error in interactive mode
from tgen.debug import exc_info_hook
sys.excepthook = exc_info_hook


def main(args):

    finished = defaultdict(int)
    input_lines = []
    skipped = defaultdict(int)
    written = defaultdict(int)

    # load input data
    with args.input_file as fh:
        csvread = csv.reader(fh, delimiter=str(args.input_csv_delim),
                             quotechar=b'"', encoding="UTF-8")
        columns = DataLine.get_columns_from_header(csvread.next())
        for row in csvread:
            input_lines.append(DataLine.from_csv_line(row, columns))

    # load all results files provided
    for finished_file in args.finished_files:
        with finished_file as fh:
            csvread = csv.reader(fh, delimiter=str(args.finished_csv_delim),
                                 quotechar=b'"', encoding="UTF-8")
            header = csvread.next();
            columns = DataLine.get_columns_from_header(header)
            try:
                judgment_column = header.index('check_result')
            except ValueError:
                judgment_column = None
            for row in csvread:
                # treat rejected as unfinished
                if judgment_column is not None and row[judgment_column].startswith('N'):
                    continue
                # keep track of how many judgments are finished in the results
                finished_line = DataLine.from_csv_line(row, columns)
                finished[finished_line.signature] += 1

    print >> sys.stderr, "Loaded input: %d, Loaded finished: %d" % (len(input_lines), len(finished))

    with sys.stdout as fh:
        # starting with the header
        csvwrite = csv.writer(fh, delimiter=b"\t", lineterminator="\n", encoding="UTF-8")
        csvwrite.writerow(DataLine.get_headers())
        # write rows requiring different number of judgments, starting from the most judgments
        for judg_req in xrange(args.num_judgments, 0, -1):

            csvwrite.writerow(("# Requiring %d judgments" % judg_req,))
            for line in input_lines:
                if finished[line.signature] != args.num_judgments - judg_req:
                    skipped[judg_req] += 1
                    continue
                csvwrite.writerow(line.as_tuple())
                written[judg_req] += 1

            print >> sys.stderr, ("%d judgments -- written: %d" % (judg_req, written[judg_req]))

    print >> sys.stderr, "Skipped: %d" % (len(input_lines) - sum(written.values()))


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('-f', '--finished-csv-delim', type=str, default=",")
    ap.add_argument('-i', '--input-csv-delim', type=str, default="\t")
    ap.add_argument('-j', '--num-judgments', type=int, default=3)
    ap.add_argument('input_file', type=FileType('r'))
    ap.add_argument('finished_files', type=FileType('r'), nargs='+')
    args = ap.parse_args()
    main(args)
