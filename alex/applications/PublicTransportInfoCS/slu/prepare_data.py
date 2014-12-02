#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

import argparse
import glob
import os
import xml.dom.minidom
import random
import sys
import multiprocessing

import alex.utils.various as various

from alex.utils.config import as_project_path
from alex.corpustools.text_norm_cs import normalise_text, exclude_slu
from alex.corpustools.wavaskey import save_wavaskey
from alex.components.asr.common import asr_factory
from alex.components.asr.utterance import Utterance, UtteranceNBList
from alex.components.slu.base import CategoryLabelDatabase
from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
from alex.applications.PublicTransportInfoCS.hdc_slu import PTICSHDCSLU
from alex.utils.config import Config

""" The script has commands:

--asr-log   it uses the asr hypotheses from call logs

"""

asr_log = 0
num_workers = 1



cldb = CategoryLabelDatabase('../data/database.py')
preprocessing = PTICSSLUPreprocessing(cldb)
slu = PTICSHDCSLU(preprocessing, cfg = {'SLU': {PTICSHDCSLU: {'utt2da': as_project_path("applications/PublicTransportInfoCS/data/utt2da_dict.txt")}}})
cfg = Config.load_configs(['../kaldi.cfg',], use_default=True)
asr_rec = asr_factory(cfg)

def normalise_semi_words(txt):
    # normalise these semi-words
    if txt == '__other__':
        txt = '_other_'
    elif txt == '__silence__':
        txt = '_other_'
    elif not txt:
        txt = '_other_'

    return txt

def process_call_log(fn):
    name = multiprocessing.current_process().name
    asr = []
    nbl = []
    sem = []
    trn = []
    trn_hdc_sem = []
    fcount = 0
    tcount = 0

    f_dir = os.path.dirname(fn)
    print "Process name:", name
    print "File #", fcount
    fcount += 1
    print "Processing:", fn
    doc = xml.dom.minidom.parse(fn)
    turns = doc.getElementsByTagName("turn")
    for i, turn in enumerate(turns):
        if turn.getAttribute('speaker') != 'user':
            continue

        recs = turn.getElementsByTagName("rec")
        trans = turn.getElementsByTagName("asr_transcription")
        asrs = turn.getElementsByTagName("asr")

        if len(recs) != 1:
            print "Skipping a turn {turn} in file: {fn} - recs: {recs}".format(turn=i, fn=fn, recs=len(recs))
            continue

        if len(asrs) == 0 and (i + 1) < len(turns):
            next_asrs = turns[i + 1].getElementsByTagName("asr")
            if len(next_asrs) != 2:
                print "Skipping a turn {turn} in file: {fn} - asrs: {asrs} - next_asrs: {next_asrs}".format(turn=i,
                                                                                                            fn=fn,
                                                                                                            asrs=len(
                                                                                                                asrs),
                                                                                                            next_asrs=len(
                                                                                                                next_asrs))
                continue
            print "Recovered from missing ASR output by using a delayed ASR output from the following turn of turn {turn}. File: {fn} - next_asrs: {asrs}".format(
                turn=i, fn=fn, asrs=len(next_asrs))
            hyps = next_asrs[0].getElementsByTagName("hypothesis")
        elif len(asrs) == 1:
            hyps = asrs[0].getElementsByTagName("hypothesis")
        elif len(asrs) == 2:
            print "Recovered from EXTRA ASR outputs by using a the last ASR output from the turn. File: {fn} - asrs: {asrs}".format(
                fn=fn, asrs=len(asrs))
            hyps = asrs[-1].getElementsByTagName("hypothesis")
        else:
            print "Skipping a turn {turn} in file {fn} - asrs: {asrs}".format(turn=i, fn=fn, asrs=len(asrs))
            continue

        if len(trans) == 0:
            print "Skipping a turn in {fn} - trans: {trans}".format(fn=fn, trans=len(trans))
            continue

        wav_key = recs[0].getAttribute('fname')
        wav_path = os.path.join(f_dir, wav_key)

        # FIXME: Check whether the last transcription is really the best! FJ
        t = various.get_text_from_xml_node(trans[-1])
        t = normalise_text(t)

        if '--asr-log' not in sys.argv:
            asr_rec_nbl = asr_rec.rec_wav_file(wav_path)
            a = unicode(asr_rec_nbl.get_best())
        else:
            a = various.get_text_from_xml_node(hyps[0])
            a = normalise_semi_words(a)

        if exclude_slu(t) or 'DOM Element:' in a:
            print "Skipping transcription:", unicode(t)
            print "Skipping ASR output:   ", unicode(a)
            continue

        # The silence does not have a label in the language model.
        t = t.replace('_SIL_', '')

        trn.append((wav_key, t))

        print
        print "Transcritpiton #", tcount
        tcount += 1
        print "Parsing transcription:", unicode(t)
        print "                  ASR:", unicode(a)

        # HDC SLU on transcription
        s = slu.parse_1_best({'utt': Utterance(t)}).get_best_da()
        trn_hdc_sem.append((wav_key, s))


        # 1 best ASR
        asr.append((wav_key, a))

        # N best ASR
        n = UtteranceNBList()
        if '--asr-log' not in sys.argv:
            n = asr_rec_nbl

            print 'ASR RECOGNITION NBLIST\n', unicode(n)
        else:
            for h in hyps:
                txt = various.get_text_from_xml_node(h)
                txt = normalise_semi_words(txt)

                n.add(abs(float(h.getAttribute('p'))), Utterance(txt))

        n.merge()
        n.normalise()

        nbl.append((wav_key, n.serialise()))

        # there is no manual semantics in the transcriptions yet
        sem.append((wav_key, None))

    return asr, nbl, sem, trn, trn_hdc_sem, fcount, tcount

def main():

    global asr_log
    global num_workers

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""This program prepares data for training Alex PTIcs SLU.
      """)

    parser.add_argument('--num_workers', action="store", default=num_workers, type=int,
                        help='number of workers used for ASR: default %d' % num_workers)
    parser.add_argument('--asr_log', action="store", default=asr_log, type=int,
                        help='use ASR results from logs: default %d' % asr_log)

    args = parser.parse_args()

    asr_log = args.asr_log
    num_workers = args.num_workers

    fn_uniq_trn = 'uniq.trn'
    fn_uniq_trn_hdc_sem = 'uniq.trn.hdc.sem'
    fn_uniq_trn_sem = 'uniq.trn.sem'

    fn_all_sem = 'all.sem'
    fn_all_trn = 'all.trn'
    fn_all_trn_hdc_sem = 'all.trn.hdc.sem'
    fn_all_asr = 'all.asr'
    fn_all_nbl = 'all.nbl'

    fn_train_sem = 'train.sem'
    fn_train_trn = 'train.trn'
    fn_train_trn_hdc_sem = 'train.trn.hdc.sem'
    fn_train_asr = 'train.asr'
    fn_train_nbl = 'train.nbl'

    fn_dev_sem = 'dev.sem'
    fn_dev_trn = 'dev.trn'
    fn_dev_trn_hdc_sem = 'dev.trn.hdc.sem'
    fn_dev_asr = 'dev.asr'
    fn_dev_nbl = 'dev.nbl'

    fn_test_sem = 'test.sem'
    fn_test_trn = 'test.trn'
    fn_test_trn_hdc_sem = 'test.trn.hdc.sem'
    fn_test_asr = 'test.asr'
    fn_test_nbl = 'test.nbl'

    indomain_data_dir = "indomain_data"

    print "Generating the SLU train and test data"
    print "-"*120
    ###############################################################################################

    files = []
    files.append(glob.glob(os.path.join(indomain_data_dir, 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data_dir, '*', 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data_dir, '*', '*', 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data_dir, '*', '*', '*', 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data_dir, '*', '*', '*', '*', 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data_dir, '*', '*', '*', '*', '*', 'asr_transcribed.xml')))
    files = various.flatten(files)

    files = files[:100000]
    asr = []
    nbl = []
    sem = []
    trn = []
    trn_hdc_sem = []


    p_process_call_logs = multiprocessing.Pool(num_workers)
    processed_cls = p_process_call_logs.imap_unordered(process_call_log, files)

    count = 0
    for pcl in processed_cls:
        count += 1
        #process_call_log(fn) # uniq utterances
        #print pcl

        print "="*80
        print "Processed files ", count, "/", len(files)
        print "="*80

        asr.extend(pcl[0])
        nbl.extend(pcl[1])
        sem.extend(pcl[2])
        trn.extend(pcl[3])
        trn_hdc_sem.extend(pcl[4])

    uniq_trn = {}
    uniq_trn_hdc_sem = {}
    uniq_trn_sem = {}
    trn_set = set()

    sem = dict(trn_hdc_sem)
    for k, v in trn:
        if not v in trn_set:
            trn_set.add(v)
            uniq_trn[k] = v
            uniq_trn_hdc_sem[k] = sem[k]
            uniq_trn_sem[k] = v + " <=> " + unicode(sem[k])

    save_wavaskey(fn_uniq_trn, uniq_trn)
    save_wavaskey(fn_uniq_trn_hdc_sem, uniq_trn_hdc_sem, trans = lambda da: '&'.join(sorted(unicode(da).split('&'))))
    save_wavaskey(fn_uniq_trn_sem, uniq_trn_sem)

    # all
    save_wavaskey(fn_all_trn, dict(trn))
    save_wavaskey(fn_all_trn_hdc_sem, dict(trn_hdc_sem), trans = lambda da: '&'.join(sorted(unicode(da).split('&'))))
    save_wavaskey(fn_all_asr, dict(asr))
    save_wavaskey(fn_all_nbl, dict(nbl))

    seed_value = 10

    random.seed(seed_value)
    random.shuffle(trn)
    random.seed(seed_value)
    random.shuffle(trn_hdc_sem)
    random.seed(seed_value)
    random.shuffle(asr)
    random.seed(seed_value)
    random.shuffle(nbl)

    # trn
    train_trn = trn[:int(0.8*len(trn))]
    dev_trn = trn[int(0.8*len(trn)):int(0.9*len(trn))]
    test_trn = trn[int(0.9*len(trn)):]

    save_wavaskey(fn_train_trn, dict(train_trn))
    save_wavaskey(fn_dev_trn, dict(dev_trn))
    save_wavaskey(fn_test_trn, dict(test_trn))

    # trn_hdc_sem
    train_trn_hdc_sem = trn_hdc_sem[:int(0.8*len(trn_hdc_sem))]
    dev_trn_hdc_sem = trn_hdc_sem[int(0.8*len(trn_hdc_sem)):int(0.9*len(trn_hdc_sem))]
    test_trn_hdc_sem = trn_hdc_sem[int(0.9*len(trn_hdc_sem)):]

    save_wavaskey(fn_train_trn_hdc_sem, dict(train_trn_hdc_sem), trans = lambda da: '&'.join(sorted(unicode(da).split('&'))))
    save_wavaskey(fn_dev_trn_hdc_sem, dict(dev_trn_hdc_sem), trans = lambda da: '&'.join(sorted(unicode(da).split('&'))))
    save_wavaskey(fn_test_trn_hdc_sem, dict(test_trn_hdc_sem), trans = lambda da: '&'.join(sorted(unicode(da).split('&'))))

    # asr
    train_asr = asr[:int(0.8*len(asr))]
    dev_asr = asr[int(0.8*len(asr)):int(0.9*len(asr))]
    test_asr = asr[int(0.9*len(asr)):]

    save_wavaskey(fn_train_asr, dict(train_asr))
    save_wavaskey(fn_dev_asr, dict(dev_asr))
    save_wavaskey(fn_test_asr, dict(test_asr))

    # n-best lists
    train_nbl = nbl[:int(0.8*len(nbl))]
    dev_nbl = nbl[int(0.8*len(nbl)):int(0.9*len(nbl))]
    test_nbl = nbl[int(0.9*len(nbl)):]

    save_wavaskey(fn_train_nbl, dict(train_nbl))
    save_wavaskey(fn_dev_nbl, dict(dev_nbl))
    save_wavaskey(fn_test_nbl, dict(test_nbl))


if __name__ == '__main__':
    main()
