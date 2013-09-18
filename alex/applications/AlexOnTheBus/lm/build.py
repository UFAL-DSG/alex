#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
import xml.dom.minidom
import glob
import codecs
import random

import autopath

import alex.corpustools.lm as lm
import alex.utils.various as various

gen_data                = lm.download_general_LM_data('cs')
gen_data_norm           = '01_norm.' +gen_data
gen_data_norm_vocab     = '02_'+gen_data_norm+'.vocab'
gen_data_norm_count1    = '03_'+gen_data_norm+'.count1'
gen_data_norm_bi_arpa   = '04_'+gen_data+'.bi.arpa'

indomain_vocab          = "indomain.vocab"
indomain_vocab_norm     = "05_norm_indomain.vocab"
indomain_ze_arpa        = "05_indomain.vocab.ze.arpa"

indomain_data                       = "indomain_data"
indomain_data_text                  = "06_indomain_data.txt"
indomain_data_text_dev              = "07_indomain_data_dev.txt"
indomain_data_text_norm             = "08_norm_indomain_data.txt"
indomain_data_text_dev_norm         = "09_norm_indomain_data_dev.txt"
indomain_data_text_dev_norm_vocab   = "09_norm_indomain_data_dev.vocab"
indomain_data_text_norm_vocab       = "10_indomain_data.vocab"
indomain_data_text_norm_count1      = "11_indomain_data.count1"
indomain_data_text_norm_bi_arpa     = "12_indomain_data.bi.arpa"

ppl_v = "13_v.ppl"
ppl_i = "14_i.ppl"
ppl_g = "15_g.ppl"
best_mix_ppl = "16_best_mix.ppl"

final_lm_vocab = "19_aotb.vocab"
final_lm = "20_aotb_interpolated.bi.arpa"

print "Data for the general language model:", gen_data

if not os.path.exists(gen_data_norm_bi_arpa):
    print "Generating general language model"

    cmd = r"zcat %s | sed 's/\. /\n/g' | tr -d '[:digit:]' | tr '\"@%%_=<>,:()[];?.|\+\-*$#!&\\/\°~`^ˇ'  ' ' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g | gzip > %s" % (gen_data, "'", gen_data_norm)
    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -write1 %s -gt1min 10 -gt2min 10 -order 2 -wbdiscount -interpolate -memuse -lm %s" % (gen_data_norm, gen_data_norm_vocab, gen_data_norm_count1, gen_data_norm_bi_arpa)
    print cmd
    os.system(cmd)
else:
    print "Using existing general language model"

print "Generating zero-gram language model from a in-domain vocabulary list"

cmd = r"cat %s | tr -d '[:digit:]' | tr '\"@%%=<>,:()[];?.|\+\-*$#!&\\/\°~`^ˇ'  ' ' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % (indomain_vocab, "'", indomain_vocab_norm)
print cmd
os.system(cmd)

cmd = "ngram-count -text %s -order 1 -wbdiscount -memuse -lm %s" % (indomain_vocab_norm, indomain_ze_arpa)
print cmd
os.system(cmd)

if not os.path.exists(indomain_data_text_norm_bi_arpa):
    print "Generating bi-gram in-domain language model from in-domain data"

    files = []
    files.append(glob.glob(os.path.join(indomain_data, 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data, '*', 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data, '*', '*', 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data, '*', '*', '*', 'asr_transcribed.xml')))
    files.append(glob.glob(os.path.join(indomain_data, '*', '*', '*', '*', 'asr_transcribed.xml')))
    # files.append(glob.glob(os.path.join(indomain_data, '*', '*', '*', '*', '*', 'asr_transcribed.xml')))
    files = various.flatten(files)

    tt = []
    for fn in files:
#            print "Processing:", fn
        doc = xml.dom.minidom.parse(fn)
        trans_list = doc.getElementsByTagName("asr_transcription")

        for trans in trans_list:
            if trans.getAttribute('breaks_gold') != '0':
                continue

            t = various.get_text_from_xml_node(trans)

            if '(unint)' in t:
                continue
            if '(unit)' in t:
                continue
            if '-' in t:
                continue

            # Here it would be useful to have a generic czech normaliser, which could be used at different places.
            # For example, also in generating transcriptions for ASR training.
            t = t.replace('(noise)', '_NOISE_')
            t = t.replace('(hum)', '_NOISE_')
            t = t.replace('(sil)', '_SIL_')
            t = t.replace('(breath)', '_INHALE_')
            t = t.replace('(laugh)', '_LAUGH_')
            tt.append(t)

    random.seed(0)
    random.shuffle(tt)
    t_train = tt[:int(0.5*len(tt))]
    t_dev = tt[int(0.5*len(tt)):]

    with codecs.open(indomain_data_text,"w", "UTF-8") as w:
        w.write('\n'.join(t_train))
    with codecs.open(indomain_data_text_dev,"w", "UTF-8") as w:
        w.write('\n'.join(t_dev))

    cmd = r"cat %s | tr -d '[:digit:]' | tr '\"@%%=<>,:()[];?.|\+\-*$#!&\\/\°~`^ˇ'  ' ' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % (indomain_data_text, "'", indomain_data_text_norm)
    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -write1 %s -gt1min 2 -gt2min 2 -order 2 -wbdiscount -interpolate -memuse -lm %s" % (indomain_data_text_norm, indomain_data_text_norm_vocab, indomain_data_text_norm_count1, indomain_data_text_norm_bi_arpa)
    print cmd
    os.system(cmd)

    cmd = r"cat %s | tr -d '[:digit:]' | tr '\"@%%=<>,:()[];?.|\+\-*$#!&\\/\°~`^ˇ'  ' ' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % (indomain_data_text_dev, "'", indomain_data_text_dev_norm)
    print cmd
    os.system(cmd)

    print "*****"
    cmd = "ngram-count -text %s -write-vocab %s" % (indomain_data_text_dev_norm, indomain_data_text_dev_norm_vocab)
    print cmd
    os.system(cmd)


else:
    print "Using existing in-domain bi-gram language model"


print
print "Test language models"

print "-"*120
print "Indomain vocabulary LM on dev in-domain data."
os.system("ngram -lm %s -ppl %s" % (indomain_ze_arpa, indomain_data_text_dev_norm))
os.system("ngram -debug 2 -lm %s -ppl %s > %s" % (indomain_ze_arpa, indomain_data_text_dev_norm, ppl_v))
print "-"*120
print "Indomain bi-gram LM on dev in-domain data."
os.system("ngram -lm %s -ppl %s" % (indomain_data_text_norm_bi_arpa, indomain_data_text_dev_norm))
os.system("ngram -debug 2 -lm %s -ppl %s > %s" % (indomain_data_text_norm_bi_arpa, indomain_data_text_dev_norm, ppl_i))
print "-"*120
print "General domain bi-gram LM on dev in-domain data."
os.system("ngram -lm %s -ppl %s" % (gen_data_norm_bi_arpa, indomain_data_text_dev_norm))
os.system("ngram -debug 2 -lm %s -ppl %s > %s" % (gen_data_norm_bi_arpa, indomain_data_text_dev_norm, ppl_g))

print "-"*120
print "Interpolating the language models"
os.system("compute-best-mix *.ppl > %s" % (best_mix_ppl,))

print "Generating final LM vocabulary"
os.system("cat %s %s %s | sed 's/[[:lower:]]*/\U&/g' | sort | uniq | grep -v '<UNK>' | grep -v '<S>' | grep -v '<\S>' > % s" % (indomain_vocab_norm, indomain_data_text_norm_vocab, indomain_data_text_dev_norm_vocab, final_lm_vocab))

with open(best_mix_ppl) as f:
    l = f.read()
    il = l.index('(')
    ir = l.rindex(')')
    l = l[il+1:ir].split(' ')
    i = [float(x) for x in l]
    print i

    cmd = "ngram -vocab %s -limit-vocab -lm %s -lambda %f  -mix-lm %s -mix-lm2 %s -mix-lambda2 %f -write-lm %s" % (final_lm_vocab, indomain_ze_arpa, i[0], indomain_data_text_norm_bi_arpa, gen_data_norm_bi_arpa, i[2], final_lm)
    print cmd
    os.system(cmd)


print "Final perplexity on dev in-domain data."
os.system("ngram -lm %s -ppl %s" % (final_lm, indomain_data_text_dev_norm))
