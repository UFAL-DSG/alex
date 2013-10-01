#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import glob
import os
import xml.dom.minidom

import autopath

import alex.utils.various as various

from alex.corpustools.text_norm_cs import normalise_text
from alex.corpustools.wavaskey import save_wavaskey
from alex.components.asr.utterance import Utterance
from alex.components.slu.base import CategoryLabelDatabase
from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
from alex.applications.PublicTransportInfoCS.hdc_slu import PTICSHDCSLU

cldb = CategoryLabelDatabase('../data/database.py')
preprocessing = PTICSSLUPreprocessing(cldb)
slu = PTICSHDCSLU(preprocessing)

fn_train_sem = 'train.sem'
fn_train_trn = 'train.trn'
fn_train_trn_hdc_sem = 'train.trn.hdc.sem'
fn_train_asr = 'train.asr'
fn_train_asr_hdc_sem = 'train.asr.hdc.sem'
fn_train_nbl = 'train.nbl'

fn_dev_sem = 'dev.sem'
fn_dev_trn = 'dev.trn'
fn_dev_trn_hdc_sem = 'dev.trn.hdc.sem'
fn_dev_asr = 'dev.asr'
fn_dev_asr_hdc_sem = 'dev.asr.hdc.sem'
fn_dev_nbl = 'dev.nbl'

fn_test_sem = 'test.sem'
fn_test_trn = 'test.trn'
fn_test_trn_hdc_sem = 'test.trn.hdc.sem'
fn_test_asr = 'test.asr'
fn_test_asr_hdc_sem = 'test.asr.hdc.sem'
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

sem = []
trn = []
trn_hdc_sem = []
asr = []
asr_hdc_sem = []
nbl = []

for fn in files:
    print "Processing:", fn
    doc = xml.dom.minidom.parse(fn)
    turns = doc.getElementsByTagName("turn")

    for turn in turns:
        if turn.getAttribute('speaker') != 'user':
            continue

        recs = turn.getElementsByTagName("rec")
        trans = turn.getElementsByTagName("asr_transcription")
        asrs = turn.getElementsByTagName("asr")

        if len(recs) != 1 or len(trans) != 1 or len(asrs) != 1:
            print "Skipping a turn in {fn}.".format(fn=fn)
            print len(recs), len(trans), len(asrs)
            continue

        hyps = asrs[0].getElementsByTagName("hypothesis")

        wav_key = recs[0].getAttribute('fname')
        t = various.get_text_from_xml_node(trans[0])
        t = normalise_text(t)

        # FIXME: We should be more tolerant and use more transcriptions
        if t != '_NOISE_' and ('-' in t or '_' in t or '(' in t):
            continue

        trn.append((wav_key, t))

        print "Parsing:", unicode(t)
        s = slu.parse_1_best({'utt':Utterance(t)}).get_best_da()
        trn_hdc_sem.append((wav_key, s))

        a = various.get_text_from_xml_node(hyps[0])
        asr.append((wav_key, a))

        s = slu.parse_1_best({'utt':Utterance(a)}).get_best_da()
        asr_hdc_sem.append((wav_key, s))

        n = [ (h.getAttribute('p'), various.get_text_from_xml_node(h)) for h in hyps ]
        nbl.append((wav_key, n))

        # there is no manual semantics in the transcriptions yet
        sem.append((wav_key, None))

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

save_wavaskey(fn_train_trn_hdc_sem, dict(train_trn_hdc_sem))
save_wavaskey(fn_dev_trn_hdc_sem, dict(dev_trn_hdc_sem))
save_wavaskey(fn_test_trn_hdc_sem, dict(test_trn_hdc_sem))

# asr
train_asr = asr[:int(0.8*len(asr))]
dev_asr = asr[int(0.8*len(asr)):int(0.9*len(asr))]
test_asr = asr[int(0.9*len(asr)):]

save_wavaskey(fn_train_asr, dict(train_asr))
save_wavaskey(fn_dev_asr, dict(dev_asr))
save_wavaskey(fn_test_asr, dict(test_asr))

# asr_hdc_sem
train_asr_hdc_sem = asr_hdc_sem[:int(0.8*len(asr_hdc_sem))]
dev_asr_hdc_sem = asr_hdc_sem[int(0.8*len(asr_hdc_sem)):int(0.9*len(asr_hdc_sem))]
test_asr_hdc_sem = asr_hdc_sem[int(0.9*len(asr_hdc_sem)):]

save_wavaskey(fn_train_asr_hdc_sem, dict(train_asr_hdc_sem))
save_wavaskey(fn_dev_asr_hdc_sem, dict(dev_asr_hdc_sem))
save_wavaskey(fn_test_asr_hdc_sem, dict(test_asr_hdc_sem))

# n-best lists
train_nbl = nbl[:int(0.8*len(nbl))]
dev_nbl = nbl[int(0.8*len(nbl)):int(0.9*len(nbl))]
test_nbl = nbl[int(0.9*len(nbl)):]

save_wavaskey(fn_train_nbl, dict(train_nbl))
save_wavaskey(fn_dev_nbl, dict(dev_nbl))
save_wavaskey(fn_test_nbl, dict(test_nbl))
