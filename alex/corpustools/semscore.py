#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

import argparse
import re
import sys
import codecs

from collections import defaultdict

from alex.utils.text import split_by

def load_semantics(file_name):
    f = codecs.open(file_name,encoding = 'UTF-8')

    semantics = defaultdict(list)
    for l in f:
        l = l.strip()
        if not l:
            continue

        l = l.split("=>")

        key = l[0].strip()
        sem = l[1].strip()

        sem = split_by(sem, '&', '(', ')', '"')

        semantics[key] = sem
    f.close()

    return semantics

def score_da(ref_da, test_da, daid):
    """Computed according to http://en.wikipedia.org/wiki/Precision_and_recall"""

    tp = 0.0
    fp = 0.0
    fn = 0.0

    statsp = defaultdict(lambda : defaultdict(float))
    epp = []

    for i in test_da:
        ri = re.sub(ur'([\w]+|\B)(="[\w\'!\., :\-)(]+")', r'\1="*"', i, flags=re.UNICODE)
        if i in ref_da:
            tp += 1.0
            statsp[ri]['tp'] += 1.0
        else:
            fp += 1.0
            statsp[ri]['fp'] += 1.0

            epp.append("""DAid {daid}
  in hyp da:                 {hypda}
  is EXTRA dai:              {dai}
  when compared with ref da: {refda}\n""".format(daid=daid, hypda='&'.join(test_da), dai=i, refda='&'.join(ref_da)))

    for i in ref_da:
        ri = re.sub(ur'([\w]+|\B)(="[\w\'!\., :\-)(]+")', r'\1="*"', i, flags=re.UNICODE)
        if i not in test_da:
            fn += 1.0
            statsp[ri]['fn'] += 1.0
            epp.append("""DAid {daid}
  in hyp da:                 {hypda}
  is MISSING dai:            {dai}
  when compared with ref da: {refda}\n""".format(daid=daid, hypda='&'.join(test_da), dai=i, refda='&'.join(ref_da)))

    return tp, fp, fn, statsp, epp

def score_file(refsem, testsem):
    tp = 0.0
    fp = 0.0
    fn = 0.0

    stats = defaultdict(lambda : defaultdict(float))
    error_output = []

    for k in sorted(refsem):
        tpp, fpp, fnp, statsp, epp  = score_da(refsem[k], testsem[k], k)
        tp += tpp
        fp += fpp
        fn += fnp
        if epp:
            error_output += [''.join(epp),]

        for kk in statsp:
            for kkk in statsp[kk]:
                stats[kk][kkk] += statsp[kk][kkk]

    precision = 100.0*tp/(tp+fp)
    recall    = 100.0*tp/(tp+fn)

    for k in stats:
        try:
            stats[k]['precision'] = 100.0*stats[k]['tp']/(stats[k]['tp']+stats[k]['fp'])
        except ZeroDivisionError:
            stats[k]['precision'] = 0.001

        try:
            stats[k]['recall'] = 100.0*stats[k]['tp']/(stats[k]['tp']+stats[k]['fn'])
        except ZeroDivisionError:
            stats[k]['recall'] = 0.001

        stats[k]['precision'] += 0.000001
        stats[k]['recall']    += 0.000001

    return precision, recall, stats, '\n'.join(error_output)

def score(fn_refsem, fn_testsem, item_level = False, detailed_error_output = False, outfile = sys.stdout):
    refsem  = load_semantics(fn_refsem)
    testsem = load_semantics(fn_testsem)

    precision, recall, stats, error_output = score_file(refsem, testsem)

    outfile.write("Ref: {r}\n".format(r=fn_refsem))
    outfile.write("Tst: {t}\n".format(t=fn_testsem))

    outfile.write("The results are based on {num_das} DAs\n".format(num_das=len(refsem)))

    outfile.write("-"*80)
    outfile.write("\n")
    outfile.write("Total precision: %6.2f" % precision)
    outfile.write("\n")
    outfile.write("Total recall:    %6.2f" % recall)
    outfile.write("\n")
    outfile.write("Total F-measure: %6.2f" % (2*precision*recall/(precision+recall), ))
    outfile.write("\n")

    if item_level:
        outfile.write("-"*80)
        outfile.write("\n")
        outfile.write("%40s %10s %10s %10s " % ('Dialogue act', 'Precision',  'Recall', 'F-measure'))
        outfile.write("\n")
        for k in sorted(stats):
            outfile.write("%40s %10.2f %10.2f %10.2f " % (k,
                                                          stats[k]['precision'],
                                                          stats[k]['recall'],
                                                          2*stats[k]['precision']*stats[k]['recall']/(stats[k]['precision']+stats[k]['recall'])
            ))
            outfile.write("\n")

        outfile.write("-"*80)
        outfile.write("\n")


    if detailed_error_output:
        outfile.write("-"*80)
        outfile.write("\n")
        outfile.write(error_output)
        outfile.write("-"*80)
        outfile.write("\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="""
    Compute scores for semantic parser output against reference semantics.
    The scores include total item precision and recall, and slot level
    precision and recall.

    The files structures must be as follows:
      sem_name    => sem_content
      ----------------------------------------
      0000001.wav => inform(food="Chinese")
      0000002.wav => request(phone)

    The semantics from the test file and the reference file is matched
    based on the sem_name.
    """)

    parser.add_argument('refsem', action="store", help='a file with reference semantics')
    parser.add_argument('testsem', action="store", help='a file with tested semantics')
    parser.add_argument('-i', action="store_true", default=False, dest="item_level", help='print item level precision and recall')
    parser.add_argument('-d', action="store_true", default=False, dest="detailed_error_output",
                        help='print missing and extra hypothesis dialogue act items')

    args = parser.parse_args()

    score(args.refsem, args.testsem, args.item_level, args.detailed_error_output)
