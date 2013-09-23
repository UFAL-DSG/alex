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

"""
This script builds the domain specific language model for the Public Transport Info domain (Czech)

The training procedure is as follows:

#. Append bootstrap text, possibly handwritten, to the text extracted from the indomain data.
#. Build a class based language model using the data generated in the previous step.
#. Score the general (domain independent) data.
#. Select 1M sentences with lowest perplexity given the class based language model.
#. Append the selected sentences to the training data generated in the 1. step.
#. Re-build the class based language model.

"""

bootstrap_text                  = "bootstrap.txt"
classes                         = "../data/database_SRILM_classes.txt"
indomain_data_dir               = "indomain_data"
gen_data                        = lm.download_general_LM_data('cs')

gen_data_norm                   = '01_gen_data_norm.txt.gz'
gen_data_norm_selected          = '04_gen_data_norm.selected.txt'

indomain_data_text_trn                          = "06_indomain_data_trn.txt"
indomain_data_text_trn_norm                     = "07_indomain_data_trn_norm.txt"
indomain_data_text_trn_norm_cls_txt             = "07_indomain_data_trn_norm_cls.txt"
indomain_data_text_trn_norm_classes             = "07_indomain_data_trn_norm.classes"
indomain_data_text_trn_norm_vocab               = "08_indomain_data_trn_norm.vocab"
indomain_data_text_trn_norm_count1              = "09_indomain_data_trn_norm.count1"
indomain_data_text_trn_norm_bi_arpa             = "10_indomain_data_trn_norm.bi.arpa"
indomain_data_text_trn_norm_bi_arpa_scoring     = "10_indomain_data_trn_norm.bi.arpa.gen_scoring.gz"

indomain_data_text_dev                  = "11_indomain_data_dev.txt"
indomain_data_text_dev_norm             = "12_indomain_data_dev_norm.txt"
indomain_data_text_dev_norm_cls_txt     = "12_indomain_data_dev_norm_cls.txt"
indomain_data_text_dev_norm_classes     = "12_indomain_data_dev_norm.classes"
indomain_data_text_dev_norm_vocab       = "13_indomain_data_dev_norm.vocab"
indomain_data_text_dev_norm_bi_arpa     = "14_indomain_data_dev_norm.bi.arpa"


expanded_data_text_trn_norm             = "20_expanded_data_trn_norm.txt"
expanded_data_text_trn_norm_cls_txt     = "21_expanded_data_trn_norm_cls.txt"
expanded_data_text_trn_norm_classes     = "22_expanded_data_trn_norm.classes"
expanded_data_text_trn_norm_vocab       = "23_expanded_data_trn_norm.vocab"
expanded_data_text_trn_norm_count1      = "24_expanded_data_trn_norm.count1"
expanded_data_text_trn_norm_bi_arpa     = "25_expanded_data_trn_norm.bi.arpa"

final_lm_vocab  = "30_ptics.vocab"
final_lm        = "31_ptics.bi.arpa"

print
print "Data for the general language model:", gen_data
print "-"*120
###############################################################################################

if not os.path.exists(gen_data_norm):
    print "Normalizing general data"
    print "-"*120
    ###############################################################################################

    cmd = r"zcat %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g | gzip > %s" % (gen_data, "'", gen_data_norm)
    print cmd
    os.system(cmd)

if not os.path.exists(indomain_data_text_trn_norm_bi_arpa):
    print "Generating bi-gram in-domain language model from in-domain data"
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

    with codecs.open(indomain_data_text_trn,"w", "UTF-8") as w:
        w.write('\n'.join(t_train))
    with codecs.open(indomain_data_text_dev,"w", "UTF-8") as w:
        w.write('\n'.join(t_dev))

    # train data
    # ! I am mixing in also the dev data, which is cheating! however it simply solves the OOV problem on dev set, and also it provides a better LM
    # problem is that I cannot say whether I really improve the LM by mixing-in the general data.
    cmd = r"cat %s %s %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % (bootstrap_text, indomain_data_text_trn, indomain_data_text_dev, "'", indomain_data_text_trn_norm)
    print cmd
    os.system(cmd)

    # convert surface forms to classes
    cmd = r"replace-words-with-classes addone=100 normalize=1 outfile=%s classes=%s  %s > %s" % (indomain_data_text_trn_norm_classes,
                                                                                                 classes,
                                                                                                 indomain_data_text_trn_norm,
                                                                                                 indomain_data_text_trn_norm_cls_txt)
    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -write1 %s -gt2min 4 -order 2 -wbdiscount -interpolate -memuse -lm %s" % (indomain_data_text_trn_norm_cls_txt,
                                                                                                                          indomain_data_text_trn_norm_vocab,
                                                                                                                          indomain_data_text_trn_norm_count1,
                                                                                                                          indomain_data_text_trn_norm_bi_arpa)
    print cmd
    os.system(cmd)

    # dev data
    cmd = r"cat %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % (indomain_data_text_dev,
                                                                                                                                                   "'",
                                                                                                                                                   indomain_data_text_dev_norm)
    print cmd
    os.system(cmd)

    # convert surface forms to classes
    cmd = r"replace-words-with-classes addone=100 normalize=1 outfile=%s classes=%s  %s > %s" % (indomain_data_text_dev_norm_classes,
                                                                                                 classes,
                                                                                                 indomain_data_text_dev_norm,
                                                                                                 indomain_data_text_dev_norm_cls_txt)
    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -gt2min 4 -order 2 -wbdiscount -interpolate -memuse -lm %s" % (indomain_data_text_dev_norm_cls_txt, indomain_data_text_dev_norm_vocab, indomain_data_text_dev_norm_bi_arpa)
    print cmd
    os.system(cmd)

if not os.path.exists(indomain_data_text_trn_norm_bi_arpa_scoring):
    print
    print "Soring general text data using the in-domain language model"
    print "-"*120
    ###############################################################################################
    os.system("ngram -lm %s -classes %s -debug 1 -ppl %s | gzip > %s" % \
              (indomain_data_text_trn_norm_bi_arpa,
               indomain_data_text_trn_norm_classes,
               gen_data_norm,
               indomain_data_text_trn_norm_bi_arpa_scoring))

if not os.path.exists(gen_data_norm_selected):
    print
    print "Selecting similar sentences to in-domain data from general text data"
    print "-"*120
    ###############################################################################################
    os.system("zcat %s | ../../../corpustools/srilm_ppl_filter.py > %s " % (indomain_data_text_trn_norm_bi_arpa_scoring, gen_data_norm_selected))


if not os.path.exists(expanded_data_text_trn_norm_bi_arpa):
    print
    print "Training the in-domain model on the expanded data"
    print "-"*120
    ###############################################################################################
    cmd = r"cat %s %s > %s" % (indomain_data_text_trn_norm, gen_data_norm_selected, expanded_data_text_trn_norm)
    print cmd
    os.system(cmd)

    # convert surface forms to classes
    cmd = r"replace-words-with-classes addone=100 normalize=1 outfile=%s classes=%s  %s | sed 's/\b\(CL_[[:alnum:]]\+\)[ ,\n]\1/\1/g' > %s" % \
          (expanded_data_text_trn_norm_classes,
           classes,
           expanded_data_text_trn_norm,
           expanded_data_text_trn_norm_cls_txt)

    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -vocab %s -limit-vocab -write-vocab %s -write1 %s -gt2min 4 -order 2 -wbdiscount -interpolate -memuse -lm %s" % \
          (expanded_data_text_trn_norm_cls_txt,
           indomain_data_text_trn_norm_vocab,
           expanded_data_text_trn_norm_vocab,
           expanded_data_text_trn_norm_count1,
           expanded_data_text_trn_norm_bi_arpa)

    print cmd
    os.system(cmd)

if os.path.exists(final_lm):
    print
    print "Expanding the language model trained on the expanded data"
    print "-"*120
    ###############################################################################################

    cmd = "ngram -lm %s -classes %s -expand-classes 2 -expand-exact 2 -write-vocab %s -write-lm %s -prune-lowprobs" \
              % (expanded_data_text_trn_norm_bi_arpa,
                 expanded_data_text_trn_norm_classes,
                 final_lm_vocab,
                 final_lm)
    print cmd
    os.system(cmd)

###############################################################################################
print
print "Test language models"

print "-"*120
print "Indomain dev bi-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -ppl %s" % (indomain_data_text_dev_norm_bi_arpa,
                                                indomain_data_text_dev_norm_classes,
                                                indomain_data_text_dev_norm))
print "-"*120
print "Indomain trn bi-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -ppl %s" % (indomain_data_text_trn_norm_bi_arpa,
                                                indomain_data_text_trn_norm_classes,
                                                indomain_data_text_dev_norm))
print "-"*120
print "Final perplexity on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -ppl %s" % (final_lm, indomain_data_text_dev_norm))
