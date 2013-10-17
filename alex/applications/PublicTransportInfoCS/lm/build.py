#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import os
import xml.dom.minidom
import glob
import codecs
import random

import autopath

import alex.corpustools.lm as lm
import alex.utils.various as various

from alex.corpustools.text_norm_cs import normalise_text


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
indomain_data_text_trn_norm_tg_arpa             = "10_indomain_data_trn_norm.tg.arpa"
indomain_data_text_trn_norm_tg_arpa_scoring     = "10_indomain_data_trn_norm.tg.arpa.gen_scoring.gz"

indomain_data_text_dev                  = "11_indomain_data_dev.txt"
indomain_data_text_dev_norm             = "12_indomain_data_dev_norm.txt"
indomain_data_text_dev_norm_cls_txt     = "12_indomain_data_dev_norm_cls.txt"
indomain_data_text_dev_norm_classes     = "12_indomain_data_dev_norm.classes"
indomain_data_text_dev_norm_vocab       = "13_indomain_data_dev_norm.vocab"
indomain_data_text_dev_norm_tg_arpa     = "14_indomain_data_dev_norm.tg.arpa"


expanded_data_text_trn_norm             = "20_expanded_data_trn_norm.txt"
expanded_data_text_trn_norm_cls_txt     = "21_expanded_data_trn_norm_cls.txt"
expanded_data_text_trn_norm_classes     = "22_expanded_data_trn_norm.classes"
expanded_data_text_trn_norm_vocab       = "23_expanded_data_trn_norm.vocab"
expanded_data_text_trn_norm_count1      = "24_expanded_data_trn_norm.count1"
expanded_data_text_trn_norm_tg_arpa             = "25_expanded_data_trn_norm.tg.arpa"
expanded_data_text_trn_norm_tg_arpa_filtered    = "25_expanded_data_trn_norm.filtered.tg.arpa"

final_lm_vocab          = "final.vocab"
final_lm_tg             = "final.tg.arpa"
final_lm_bg             = "final.bg.arpa"
final_lm_bg_wdnet       = "final.bg.wdnet"
final_lm_dict           = "final.dict"
final_lm_dict_sp_sil    = "final.dict.sp_sil"

print
print "Data for the general language model:", gen_data
print "-"*120
###############################################################################################

if not os.path.exists(gen_data_norm):
    print "Normalizing general data"
    print "-"*120
    ###############################################################################################

    cmd = r"zcat %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g | gzip > %s" % \
          (gen_data,
           "'",
           gen_data_norm)

    print cmd
    os.system(cmd)

if not os.path.exists(indomain_data_text_trn_norm_tg_arpa):
    print "Generating 3-gram in-domain language model from in-domain data"
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
        turns = doc.getElementsByTagName("turn")
        
        for turn in turns: 
            trans_list = turn.getElementsByTagName("asr_transcription")

	    if trans_list:
    		trans = trans_list[-1]

                t = various.get_text_from_xml_node(trans)

	        if '(unint)' in t:
    	    	    continue
        	if '(unit)' in t:
            	    continue
        	if '-' in t:
            	    continue

        	tt.append(normalise_text(t))

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
    cmd = r"cat %s %s %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]_]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % \
          (bootstrap_text,
           indomain_data_text_trn,
           indomain_data_text_dev,
           "'",
           indomain_data_text_trn_norm)

    print cmd
    os.system(cmd)

    # convert surface forms to classes
    cmd = r"replace-words-with-classes addone=100 normalize=1 outfile=%s classes=%s %s > %s" % \
          (indomain_data_text_trn_norm_classes,
           classes,
           indomain_data_text_trn_norm,
           indomain_data_text_trn_norm_cls_txt)

    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -write1 %s -order 3 -wbdiscount -interpolate -memuse -lm %s" % \
          (indomain_data_text_trn_norm_cls_txt,
           indomain_data_text_trn_norm_vocab,
           indomain_data_text_trn_norm_count1,
           indomain_data_text_trn_norm_tg_arpa)

    print cmd
    os.system(cmd)

    # dev data
    cmd = r"cat %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]_]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % \
          (indomain_data_text_dev,
          "'",
          indomain_data_text_dev_norm)
    print cmd
    os.system(cmd)

    # convert surface forms to classes
    cmd = r"replace-words-with-classes addone=100 normalize=1 outfile=%s classes=%s %s  > %s" % \
          (indomain_data_text_dev_norm_classes,
           classes,
           indomain_data_text_dev_norm,
           indomain_data_text_dev_norm_cls_txt)

    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -order 3 -wbdiscount -interpolate -memuse -lm %s" % (indomain_data_text_dev_norm_cls_txt, indomain_data_text_dev_norm_vocab, indomain_data_text_dev_norm_tg_arpa)
    print cmd
    os.system(cmd)

if not os.path.exists(indomain_data_text_trn_norm_tg_arpa_scoring):
    print
    print "Soring general text data using the in-domain language model"
    print "-"*120
    ###############################################################################################
    os.system("ngram -lm %s -classes %s -debug 1 -ppl %s | gzip > %s" % \
              (indomain_data_text_trn_norm_tg_arpa,
               indomain_data_text_trn_norm_classes,
               gen_data_norm,
               indomain_data_text_trn_norm_tg_arpa_scoring))

if not os.path.exists(gen_data_norm_selected):
    print
    print "Selecting similar sentences to in-domain data from general text data"
    print "-"*120
    ###############################################################################################
    os.system("zcat %s | ../../../corpustools/srilm_ppl_filter.py > %s " % (indomain_data_text_trn_norm_tg_arpa_scoring, gen_data_norm_selected))


if not os.path.exists(expanded_data_text_trn_norm_tg_arpa):
    print
    print "Training the in-domain model on the expanded data"
    print "-"*120
    ###############################################################################################
    cmd = r"cat %s %s > %s" % (indomain_data_text_trn_norm, gen_data_norm_selected, expanded_data_text_trn_norm)
    print cmd
    os.system(cmd)

    # convert surface forms to classes
    # | sed 's/\b\(CL_[[:alnum:]]\+\)[ ,\n]\1/\1/g' | grep -v 'CL_[[:alnum:]]\+ CL_'
    cmd = r"replace-words-with-classes addone=100 normalize=1 outfile=%s classes=%s %s > %s" % \
          (expanded_data_text_trn_norm_classes,
           classes,
           expanded_data_text_trn_norm,
           expanded_data_text_trn_norm_cls_txt)

    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -vocab %s -limit-vocab -write-vocab %s -write1 %s -order 3 -wbdiscount -interpolate -memuse -lm %s" % \
          (expanded_data_text_trn_norm_cls_txt,
           indomain_data_text_trn_norm_vocab,
           expanded_data_text_trn_norm_vocab,
           expanded_data_text_trn_norm_count1,
           expanded_data_text_trn_norm_tg_arpa)

    print cmd
    os.system(cmd)

    cmd = "cat %s | grep -v 'CL_[[:alnum:]_]\+[[:alnum:] ]\+CL_'> %s" % \
          (expanded_data_text_trn_norm_tg_arpa,
           expanded_data_text_trn_norm_tg_arpa_filtered)

    print cmd
    os.system(cmd)

    cmd = "ngram -lm %s -renorm -write-lm %s" % \
          (expanded_data_text_trn_norm_tg_arpa_filtered,
           expanded_data_text_trn_norm_tg_arpa_filtered)

    print cmd
    os.system(cmd)

if not os.path.exists(final_lm_tg):
    print
    print "Expanding the language model trained on the expanded data"
    print "-"*120
    ###############################################################################################

    cmd = "ngram -lm %s -classes %s -expand-classes 0 -expand-exact 0 -write-vocab %s -write-lm %s -prune-lowprobs -prune 0.0000001" \
              % (expanded_data_text_trn_norm_tg_arpa_filtered,
                 expanded_data_text_trn_norm_classes,
                 final_lm_vocab,
                 final_lm_tg)
    print cmd
    os.system(cmd)

    cmd = "ngram -lm %s -order 3 -write-lm %s -prune-lowprobs -prune 0.0000001" \
              % (final_lm_tg,
                 final_lm_tg)
    print cmd
    os.system(cmd)

    cmd = "ngram -lm %s -order 2 -write-lm %s -prune-lowprobs -prune 0.0000001" \
              % (final_lm_tg,
                 final_lm_bg)
    print cmd
    os.system(cmd)

    cmd = "HBuild -A -T 1 -C ../../../tools/asr/common/configrawmit -u '<UNK>' -s '<s>' '</s>' -n %s -z %s %s" % \
          (final_lm_bg,
           final_lm_vocab,
           final_lm_bg_wdnet)

    os.system(cmd)

    cmd = "cat %s | grep -v '\-pau\-' | grep -v '<s>' | grep -v '</s>' | grep -v '<unk>' > %s && mv %s %s " % \
          (final_lm_vocab,
           final_lm_vocab+".tmp",
           final_lm_vocab+".tmp",
           final_lm_vocab)

    print cmd
    os.system(cmd)

    cmd = """
    echo "<s>	[] sil" > {dict} &&
    echo "</s>	[] sil" >> {dict} &&
    echo "silence	sil" >> {dict} &&
    echo "_INHALE_	_inhale_" >> {dict} &&
    echo "_LAUGH_	_laugh_" >> {dict} &&
    echo "_EHM_HMM_	_ehm_hmm_" >> {dict} &&
    echo "_NOISE_	_noise_" >> {dict} &&
    echo "_SIL_	sil" >> {dict}
    """.format(dict=final_lm_dict)

    print cmd
    os.system(cmd)

    cmd = "perl ../../../tools/asr/bin/PhoneticTranscriptionCS.pl %s %s" % \
          (final_lm_vocab,
           final_lm_dict)

    print cmd
    os.system(cmd)

    cmd = "perl ../../../tools/asr/bin/AddSp.pl %s 1 > %s " % \
          (final_lm_dict,
          final_lm_dict_sp_sil)

    print cmd
    os.system(cmd)

###############################################################################################
print
print "Test language models"

print "-"*120
print "Indomain dev 3-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -ppl %s" % (indomain_data_text_dev_norm_tg_arpa,
                                                indomain_data_text_dev_norm_classes,
                                                indomain_data_text_dev_norm))
print "-"*120
print "Indomain trn 3-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -ppl %s" % (indomain_data_text_trn_norm_tg_arpa,
                                                indomain_data_text_trn_norm_classes,
                                                indomain_data_text_dev_norm))
print "-"*120
print "Expanded trn 3-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -ppl %s" % (expanded_data_text_trn_norm_tg_arpa_filtered,
                                                expanded_data_text_trn_norm_classes,
                                                indomain_data_text_dev_norm))
print "-"*120
print "Final 3-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -ppl %s" % (final_lm_tg, indomain_data_text_dev_norm))

print "-"*120
print "Final 2-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -ppl %s" % (final_lm_bg, indomain_data_text_dev_norm))
