#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Normalize and build the Alex Context NLG Dataset"""

from __future__ import unicode_literals
from argparse import ArgumentParser, FileType
import sys
import unicodecsv as csv
import re
import codecs
from collections import defaultdict
import json
import random

import hunspell
from util import *


spellchecker = hunspell.HunSpell('/usr/share/hunspell/en_US.dic', '/usr/share/hunspell/en_US.aff')

# normalizing spelling variants and fixing typos
SPELL_FIXES = {'apologise': 'apologize',
               'travelling': 'traveling',
               'travelled': 'traveled',
               'okay': 'ok',
               'dir': 'direction',
               'undertand': 'understand',
               'adn': 'and',
               'aoologies': 'apologies',
               'ar': 'are',
               'directin': 'direction',
               'conections': 'connections',
               'centrall': 'central',
               'fromn': 'from',
               'cortandt': 'cortlandt',
               'confrim': 'confirm',
               'confrirm': 'confirm',
               'looing': 'looking',
               'altenative': 'alternative',
               'alterative': 'alternative',
               'alernate': 'alternate',
               'fron': 'from',
               'arrivive': 'arrive',
               'soory': 'sorry',
               'grom': 'from',
               'shedule': 'schedule',
               'connecion': 'connection',
               'whre': 'where',
               'lne': 'line',
               'cound': 'could',
               }

# possible relative times used in the dataset (for reparsing)
REL_TIMES = {'ten minutes': '0:10',
             'quarter an hour': '0:15',
             'fifteen minutes': '0:15',
             'twenty minutes': '0:20',
             'thirty minutes': '0:30',
             'half an hour': '0:30'}

# possible hour numbers used in the dataset (for reparsing)
HOURS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six',
         'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']

# a list of acceptable words that Hunspell won't accept
CUSTOM_DICT = set([',', ';', ':', '?', '!', '.',
                   'ok',
                   'i\'m', 'i', 'i\'ll', 'i\'ve', 'i\'d',
                   'alrighty'])

# alternative realization of slot values for delexicalization
ALT_VALUES = {'pm': ['afternoon', 'evening'],
              'am': ['morning'],
              '0': ['no', 'zero', 'none', 'any'],
              '1': ['one'],
              '2': ['two', 'second', '2nd'],
              '1:00': ['one o\'clock', 'one', '1'],
              '2:00': ['two o\'clock', 'two', '2'],
              '3:00': ['three o\'clock', 'three', '3'],
              '4:00': ['four o\'clock', 'four', '4'],
              '5:00': ['five o\'clock', 'five', '5'],
              '6:00': ['six o\'clock', 'six', '6'],
              '7:00': ['seven o\'clock', 'seven', '7'],
              '8:00': ['eight o\'clock', 'eight', '8'],
              '9:00': ['nine o\'clock', 'nine', '9'],
              '10:00': ['ten o\'clock', 'ten', '10'],
              '11:00': ['eleven o\'clock', 'eleven', '11'],
              '12:00': ['twelve o\'clock', 'twelve', '12'],
              '0:30': ['half', 'thirty', '30'],
              '0:20': ['twenty', '20'],
              '0:15': ['quarter', 'fifteen', '15'],
              '0:10': ['ten', '10'], }

# random seed for final shuffling
RAND_SEED = 1206


def reparse_time(utt):
    # relative times
    for expr, val in REL_TIMES.iteritems():
        if expr in utt:
            return val
    # absolute times
    for hour in HOURS:
        if hour + ' thirty' in utt:
            return str(HOURS.index(hour)) + ':30'
        elif hour in utt:
            return str(HOURS.index(hour)) + ':00'
    raise ValueError('Cannot find time value: ' + utt)


def reparse_ampm(utt):
    if re.search(r'\bmorning\b', utt):
        return 'am'
    if re.search(r'\b(afternoon|evening)\b', utt):
        return 'pm'
    if re.search(r'(zero|one|two|three|four|five|six|seven|eight|nine' +
                 r'|ten|eleven|twelve|thirty|clock|\*NUMBER) (am|a m)\b', utt):
        return 'am'
    if re.search(r'\b(pm|p m)\b', utt):
        return 'pm'
    raise ValueError('Cannot find AMPM value: ' + utt)


def convert_parse(data_line):
    """Convert the DA format in the SLU parse to standard Alex DA format."""
    ret = data_line.abstr_da
    ret = ret.replace('*STREET', '*STOP')
    ret = re.sub(r'(request\([a-z_]+)="\*[A-Z_]+"\)', r'\1)', ret)
    return ret


def lexicalize_parse(data_line, delex_parse):
    """Lexicalize abstract SLU parse (with values from the lexicalized reply)."""
    ret = delex_parse
    svs = data_line.slot_values
    for slot, value in svs.iteritems():
        delex_value = '*' + slot.upper()
        if 'time' in slot and delex_value in ret:
            value = reparse_time(data_line.utt)
        elif slot == 'ampm' and delex_value in ret:
            value = reparse_ampm(data_line.utt)
        ret = ret.replace(delex_value, value)
    return ret


def convert_da(data_line, delex=False):
    """Convert DA into Alex format (and possibly delexicalize)."""
    da = data_line.da
    if ';' in da:
        da = da.split('; ')
    else:
        da = [data_line.dat + ': ' + da]

    ret = []
    for da_part in da:
        dat, slots = da_part.split(': ')
        # convert DA types into Alex format
        if dat == 'reply':
            dat = 'inform'
        elif dat == 'apologize':
            dat = 'inform_no_match'
        elif dat == 'confirm':
            dat = 'iconfirm'
        # conevrt slots and values
        slots = [slot.split('=') for slot in slots.split(', ') if 'notfound' not in slot]
        if delex:
            ret.extend([dat + '(' + slot_name + ('="*' + slot_name.upper() + '"' if val != '?' else '') + ')'
                        for slot_name, val in slots])
        else:
            ret.extend([dat + '(' + slot_name + ('="' + val + '"' if val != '?' else '') + ')'
                        for slot_name, val in slots])
    return '&'.join(ret)


def ask(data_line, response_text, question):
    """Ask a question, printing the current DA and response above it."""
    printout(data_line.dat + ' ' + data_line.da + "\n", colour=RED)
    printout(response_text + "\n", colour=BLUE)
    raw_result = raw_input(question)
    return raw_result.strip()


def normalize_response(response_text, data_line):
    """Normalize response text:

    * capitalization
    * spacing
    * final punctuation
    * spelling variants
    * spellcheck
    """
    toks = ' ' + response_text + ' '  # pad with spaces for easy regexes

    # bugfix, 0:00pm -> 12:00pm
    toks = re.sub(r'\b0:([0-9][0-9]\s*[ap]m)\b', r'12:\1', toks)

    # find out data items, store them to exclude from spell checking
    data_toks = set()
    for data_item in data_line.values_list:
        data_toks.update(data_item.lower().split(' '))

    # tokenize
    toks = re.sub(r'([?.!;,:-]+)(?![0-9])', r' \1 ', toks)  # enforce space around all punct
    toks = re.sub(r'\s+', ' ', toks)

    if 'am' in data_line.values_list or 'pm' in data_line.values_list:
        toks = re.sub(r'([0-9])([apAP][mM])\b', r'\1 \2', toks)  # separate time & am/pm (acc. to DA)

    toks = toks.lower()  # work out spelling in lowercase

    # spelling fixes
    toks = re.sub(r'\bcan not\b', 'cannot', toks)

    toks = toks[1:-1].split(' ')  # remove the padding spaces and split
    toks = [SPELL_FIXES.get(tok, tok) for tok in toks]

    # spelling checks
    toks_out = []
    for tok in toks:
        if tok not in data_toks and tok not in CUSTOM_DICT and not spellchecker.spell(tok):
            resp = ask(data_line, response_text,
                       'Correct spelling of `%s\' -- [A]ll/[S]kip (text of post-edit): ' % tok)
            if resp.upper() == 'S':
                toks_out.append(tok)
                continue
            elif resp.upper().startswith('A '):
                resp = resp[2:]
                SPELL_FIXES[tok] = resp
            toks_out.append(resp)
        else:
            toks_out.append(tok)

    toks = ' ' + ' '.join(toks_out) + ' '

    # normalize capitalization
    toks = re.sub(r'\bi\b', 'I', toks)
    toks = re.sub(r'\bok\b', 'OK', toks)
    toks = re.sub(r'([?.!]|^) ([a-z])',
                  lambda match: match.group(1) + ' ' + match.group(2).upper(),
                  toks)

    for data_item in data_line.values_list:  # capitalization of data items
        if data_item == data_item.lower():
            continue
        toks = re.sub(r'\b' + data_item + r'\b', data_item, toks, flags=re.IGNORECASE)

    toks = re.sub(r' ([?.!;,:-]+)', r'\1', toks)  # remove space before punctuation
    toks = toks[1:-1]  # remove padding spaces

    # check if final punctuation matches the type
    if re.match(r'^(confirm|reply|apologize|confirm&reply)$', data_line.dat) and toks.endswith('?'):
        resp = ask(data_line, response_text, "Change final punctuation to `.'? [Y/N]: ")
        if resp.upper() == 'Y':
            toks = toks[:-1] + '.'
    if (re.match(r'^(request|confirm&request)$', data_line.dat) and
            (toks.endswith('.') or toks.endswith('!')) and
            not re.match(r'^(Please (tell|provide|let me know) |I(\'m going to)? need)', toks)):
        resp = ask(data_line, response_text, "Change final punctuation to `?'? [Y/N]: ")
        if resp.upper() == 'Y':
            toks = toks[:-1] + '?'

    # add final punctuation if not present
    if toks[-1] not in ['.', '!', '?']:
        if re.match(r'^(confirm|reply|apologize|confirm-reply)$', data_line.dat):
            toks += '.'
        elif re.match(r'^(request|confirm-request)$', data_line.dat):
            toks += '?'

    # fix at 0:30 -> in 0:30 if needed
    if 'departure_time_rel' in data_line.slots and re.search(r'\bat 0:[0-9][0-9]\b', toks):
        resp = ask(data_line, response_text, "Change `at' to `in'? [Y/N]: ")
        if resp.upper() == 'Y':
            toks = re.sub(r'\bat (0:[0-9][0-9])\b', r'in \1', toks)

    return toks


def delexicalize(response_text, data_line):
    """Delexicalize (normalized) response text."""
    text = response_text
    for slot, value in data_line.slot_values.iteritems():
        if slot == 'alternative':
            if value == '2':
                for val in ['second', '2nd']:
                    text = re.sub(r'\b' + val + r'\b', '*ALTERNATIVE-th', text, flags=re.IGNORECASE)
            else:
                continue
        # check if the value to be delexicalized is actually present
        if not any(re.search(r'\b' + val + r'\b', response_text, re.IGNORECASE)
                   for val in [value] + ALT_VALUES.get(value, [])):
            raise ValueError("Cannot find value `%s=%s' in response `%s'!" % (slot, value, response_text))
        # delexicalize
        for val in [value] + ALT_VALUES.get(value, []):
            pre_context = r'(?<!\.)\b'  # avoid parts of numbers being changed
            if val == 'am':
                pre_context = r'(?<!I )\b'  # avoid 'am' in 'I am'
            text = re.sub(pre_context + val + r'\b', '*' + slot.upper(), text, flags=re.IGNORECASE)
    return text


def main(args):

    finished = defaultdict(list)
    input_lines = []

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
            header = csvread.next()
            columns = DataLine.get_columns_from_header(header)
            try:
                judgment_column = header.index('check_result')
            except ValueError:
                judgment_column = None
            for row in csvread:
                # treat rejected/unchecked as unfinished
                if judgment_column is None or not row[judgment_column] or not row[judgment_column][0] in ['Y', 'E']:
                    continue
                # save all accepted finished lines
                finished[DataLine.from_csv_line(row, columns).signature].append(Result(row, header))

    print >> sys.stderr, "Loaded input: %d, Loaded finished: %d" % (len(input_lines), len(finished))

    out_lines = []
    out_headers = ['context_utt', 'context_freq', 'context_parse', 'response_da',
                   'response_nl1', 'response_nl2', 'response_nl3',
                   'context_utt_l', 'context_parse_l', 'response_da_l',
                   'response_nl1_l', 'response_nl2_l', 'response_nl3_l']

    for num, line in enumerate(input_lines):
        if not finished[line.signature]:
            continue
        res = finished[line.signature]

        if len(res) > 3:
            print >> sys.stderr, 'WARN: Total %d responses for the signature %s' % (len(res), line.signature)

        # create output line
        out_line = Result([''] * len(out_headers), out_headers)
        out_line.context_utt = line.abstr_utt
        out_line.context_utt_l = line.utt
        out_line.context_parse = convert_parse(line)
        out_line.context_parse_l = lexicalize_parse(line, out_line.context_parse)
        out_line.response_da = convert_da(line, delex=True)
        out_line.response_da_l = convert_da(line)
        out_line.context_freq = line.occ_num

        out_line.response_nl1_l = normalize_response(res[0].reply, line)
        out_line.response_nl1 = delexicalize(out_line.response_nl1_l, line)
        printout(str(num) + ' ' + out_line.response_da_l + "\n")
        printout(out_line.response_nl1_l + "\n", colour=YELLOW)

        if len(res) > 1:
            out_line.response_nl2_l = normalize_response(res[1].reply, line)
            out_line.response_nl2 = delexicalize(out_line.response_nl2_l, line)
            printout(out_line.response_nl2_l + "\n", colour=YELLOW)

        if len(res) > 2:
            out_line.response_nl3_l = normalize_response(res[2].reply, line)
            out_line.response_nl3 = delexicalize(out_line.response_nl3_l, line)
            printout(out_line.response_nl3_l + "\n", colour=YELLOW)

        out_lines.append(out_line)

    # shuffle the order for the output (but keep it consistent)
    random.seed(RAND_SEED)
    random.shuffle(out_lines)

    print >> sys.stderr, 'Writing CSV to %s' % (args.output_file_name + '.csv')
    # write the CSV
    with open(args.output_file_name + '.csv', 'wb') as fh:
        # starting with the header
        csvwrite = csv.writer(fh, delimiter=b",", lineterminator="\n", encoding="UTF-8")
        csvwrite.writerow(out_headers)
        for out_line in out_lines:
            csvwrite.writerow(out_line.as_array())

    print >> sys.stderr, 'Writing JSON to %s' % (args.output_file_name + '.json')
    # write JSON
    with codecs.open(args.output_file_name + '.json', 'wb', 'UTF-8') as fh:

        # convert the data format
        out_data = [out_line.as_dict() for out_line in out_lines]
        for out_line in out_data:
            out_line['context_freq'] = int(out_line['context_freq'])
            out_line['response_nl'] = [out_line['response_nl1'],
                                       out_line['response_nl2'],
                                       out_line['response_nl3']]
            out_line['response_nl_l'] = [out_line['response_nl1_l'],
                                         out_line['response_nl2_l'],
                                         out_line['response_nl3_l']]
            del out_line['response_nl1']
            del out_line['response_nl1_l']
            del out_line['response_nl2']
            del out_line['response_nl2_l']
            del out_line['response_nl3']
            del out_line['response_nl3_l']

        json.dump(out_data, fh, ensure_ascii=False, indent=4, sort_keys=True)


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('-f', '--finished-csv-delim', type=str, default=",")
    ap.add_argument('-i', '--input-csv-delim', type=str, default="\t")
    ap.add_argument('input_file', type=FileType('r'))
    ap.add_argument('output_file_name', type=str)
    ap.add_argument('finished_files', type=FileType('r'), nargs='+')
    args = ap.parse_args()
    main(args)
