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

from alex.corpustools.text_norm_cs import normalise_text, exclude_lm


bootstrap_text                  = "bootstrap.txt"
classes                         = "../data/database_SRILM_classes.txt"
indomain_data_dir               = "indomain_data"
gen_data                        = lm.download_general_LM_data('cs')

gen_data_norm                   = '01_gen_data_norm.txt.gz'
gen_data_norm_selected          = '04_gen_data_norm.selected.txt'

indomain_data_text_trn                          = "06_indomain_data_trn.txt"
indomain_data_text_trn_norm                     = "07_indomain_data_trn_norm.txt"
indomain_data_text_trn_norm_vocab               = "07_indomain_data_trn_norm.txt.vocab"
indomain_data_text_trn_norm_count1              = "07_indomain_data_trn_norm.txt.count1"
indomain_data_text_trn_norm_pg_arpa             = "07_indomain_data_trn_norm.txt.pg.arpa"
indomain_data_text_trn_norm_cls                 = "07_indomain_data_trn_norm_cls.txt"
indomain_data_text_trn_norm_cls_classes         = "07_indomain_data_trn_norm_cls.classes"
indomain_data_text_trn_norm_cls_vocab           = "08_indomain_data_trn_norm_cls.vocab"
indomain_data_text_trn_norm_cls_count1          = "09_indomain_data_trn_norm_cls.count1"
indomain_data_text_trn_norm_cls_pg_arpa         = "10_indomain_data_trn_norm_cls.pg.arpa"
indomain_data_text_trn_norm_cls_pg_arpa_scoring = "10_indomain_data_trn_norm_cls.pg.arpa.gen_scoring.gz"

indomain_data_text_dev                      = "11_indomain_data_dev.txt"
indomain_data_text_dev_norm                 = "12_indomain_data_dev_norm.txt"
indomain_data_text_dev_norm_cls             = "12_indomain_data_dev_norm_cls.txt"
indomain_data_text_dev_norm_cls_classes     = "12_indomain_data_dev_norm_cls.classes"
indomain_data_text_dev_norm_cls_vocab       = "13_indomain_data_dev_norm_cls.vocab"
indomain_data_text_dev_norm_cls_pg_arpa     = "14_indomain_data_dev_norm_cls.pg.arpa"


extended_data_text_trn_norm                         = "20_extended_data_trn_norm.txt"
extended_data_text_trn_norm_cls                     = "21_extended_data_trn_norm_cls.txt"
extended_data_text_trn_norm_cls_classes             = "22_extended_data_trn_norm_cls.classes"
extended_data_text_trn_norm_cls_vocab               = "23_extended_data_trn_norm_cls.vocab"
extended_data_text_trn_norm_cls_count1              = "24_extended_data_trn_norm_cls.count1"
extended_data_text_trn_norm_cls_pg_arpa             = "25_extended_data_trn_norm_cls.pg.arpa"
extended_data_text_trn_norm_cls_pg_arpa_filtered    = "25_extended_data_trn_norm_cls.filtered.pg.arpa"

expanded_lm_vocab       = "26_expanded.vocab"
expanded_lm_pg          = "26_expanded.pg.arpa"

mixing_weight           = "0.8"
mixed_lm_vocab          = "27_mixed.vocab"
mixed_lm_pg             = "27_mixed.pg.arpa"

final_lm_vocab          = "final.vocab"
final_lm_pg             = "final.pg.arpa"
final_lm_qg             = "final.qg.arpa"
final_lm_tg             = "final.tg.arpa"
final_lm_bg             = "final.bg.arpa"
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

if not os.path.exists(indomain_data_text_trn_norm):
    print "Generating train and dev data"
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
                t = normalise_text(t)

                if exclude_lm(t):
                    continue

                # The silence does not have a label in the language model.
                t = t.replace('_SIL_', '')

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
    cmd = r"cat %s %s %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]_]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % \
          (bootstrap_text,
           indomain_data_text_trn,
           indomain_data_text_dev,
           "'",
           indomain_data_text_trn_norm)

    print cmd
    os.system(cmd)

if not os.path.exists(indomain_data_text_trn_norm_cls_pg_arpa):
    print "Generating class-based 5-gram in-domain language model from in-domain data"
    print "-"*120
    ###############################################################################################
    # convert surface forms to classes
    cmd = r"replace-words-with-classes addone=10 normalize=1 outfile=%s classes=%s %s > %s" % \
          (indomain_data_text_trn_norm_cls_classes,
           classes,
           indomain_data_text_trn_norm,
           indomain_data_text_trn_norm_cls)

    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -write1 %s -order 5 -wbdiscount -interpolate -memuse -lm %s" % \
          (indomain_data_text_trn_norm_cls,
           indomain_data_text_trn_norm_cls_vocab,
           indomain_data_text_trn_norm_cls_count1,
           indomain_data_text_trn_norm_cls_pg_arpa)

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
    cmd = r"replace-words-with-classes addone=10 normalize=1 outfile=%s classes=%s %s  > %s" % \
          (indomain_data_text_dev_norm_cls_classes,
           classes,
           indomain_data_text_dev_norm,
           indomain_data_text_dev_norm_cls)

    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -write-vocab %s -order 5 -wbdiscount -interpolate -memuse -lm %s" % \
          (indomain_data_text_dev_norm_cls,
           indomain_data_text_dev_norm_cls_vocab,
           indomain_data_text_dev_norm_cls_pg_arpa)
    print cmd
    os.system(cmd)

if not os.path.exists(indomain_data_text_trn_norm_pg_arpa):
    print
    print "Generating full 5-gram in-domain language model from in-domain data"
    print "-"*120
    cmd = "ngram-count -text %s -write-vocab %s -write1 %s -order 5 -wbdiscount -interpolate -memuse -lm %s" % \
          (indomain_data_text_trn_norm,
           indomain_data_text_trn_norm_vocab,
           indomain_data_text_trn_norm_count1,
           indomain_data_text_trn_norm_pg_arpa)

    print cmd
    os.system(cmd)

if not os.path.exists(indomain_data_text_trn_norm_cls_pg_arpa_scoring):
    print
    print "Scoring general text data using the in-domain language model"
    print "-"*120
    ###############################################################################################
    os.system("ngram -lm %s -classes %s -order 5 -debug 1 -ppl %s | gzip > %s" % \
              (indomain_data_text_trn_norm_cls_pg_arpa,
               indomain_data_text_trn_norm_cls_classes,
               gen_data_norm,
               indomain_data_text_trn_norm_cls_pg_arpa_scoring))

if not os.path.exists(gen_data_norm_selected):
    print
    print "Selecting similar sentences to in-domain data from general text data"
    print "-"*120
    ###############################################################################################
    os.system("zcat %s | ../../../corpustools/srilm_ppl_filter.py > %s " % (indomain_data_text_trn_norm_cls_pg_arpa_scoring, gen_data_norm_selected))


if not os.path.exists(extended_data_text_trn_norm_cls_pg_arpa):
    print
    print "Training the in-domain model on the extended data"
    print "-"*120
    ###############################################################################################
    cmd = r"cat %s %s > %s" % (indomain_data_text_trn_norm, gen_data_norm_selected, extended_data_text_trn_norm)
    print cmd
    os.system(cmd)

    # convert surface forms to classes
    cmd = r"replace-words-with-classes addone=10 normalize=1 outfile=%s classes=%s %s > %s" % \
          (extended_data_text_trn_norm_cls_classes,
           classes,
           extended_data_text_trn_norm,
           extended_data_text_trn_norm_cls)

    print cmd
    os.system(cmd)

    cmd = "ngram-count -text %s -vocab %s -limit-vocab -write-vocab %s -write1 %s -order 5 -wbdiscount -interpolate -memuse -lm %s" % \
          (extended_data_text_trn_norm_cls,
           indomain_data_text_trn_norm_cls_vocab,
           extended_data_text_trn_norm_cls_vocab,
           extended_data_text_trn_norm_cls_count1,
           extended_data_text_trn_norm_cls_pg_arpa)

    print cmd
    os.system(cmd)

    cmd = "cat %s | grep -v 'CL_[[:alnum:]_]\+[[:alnum:] _]\+CL_'> %s" % \
          (extended_data_text_trn_norm_cls_pg_arpa,
           extended_data_text_trn_norm_cls_pg_arpa_filtered)

    print cmd
    os.system(cmd)

    cmd = "ngram -lm %s -order 5 -renorm -write-lm %s" % \
          (extended_data_text_trn_norm_cls_pg_arpa_filtered,
           extended_data_text_trn_norm_cls_pg_arpa_filtered)

    print cmd
    os.system(cmd)

if not os.path.exists(expanded_lm_pg):
    print
    print "Expanding the language model"
    print "-"*120
    ###############################################################################################

    cmd = "ngram -lm %s -classes %s -order 5 -expand-classes 5 -write-vocab %s -write-lm %s -renorm" \
              % (extended_data_text_trn_norm_cls_pg_arpa_filtered,
                 extended_data_text_trn_norm_cls_classes,
                 expanded_lm_vocab,
                 expanded_lm_pg)
    print cmd
    os.system(cmd)

if not os.path.exists(mixed_lm_pg):
    print
    print "Mixing the expanded class-based model and the full model"
    print "-"*120
    ###############################################################################################

    cmd = "ngram -lm %s -mix-lm %s -lambda %s -order 5 -write-vocab %s -write-lm %s -prune 0.000000001 -renorm" \
              % (expanded_lm_pg,
                 indomain_data_text_trn_norm_pg_arpa,
                 mixing_weight,
                 mixed_lm_vocab,
                 mixed_lm_pg)
    print cmd
    os.system(cmd)

if not os.path.exists(final_lm_pg):
    print
    print "Building the final language models"
    print "-"*120
    ###############################################################################################

    cmd = "ngram -lm %s -order 5 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
              % (mixed_lm_pg,
                 final_lm_pg)
    print cmd
    os.system(cmd)

    cmd = "ngram -lm %s -order 4 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
              % (mixed_lm_pg,
                 final_lm_qg)
    print cmd
    os.system(cmd)

    cmd = "ngram -lm %s -order 3 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
              % (mixed_lm_pg,
                 final_lm_tg)
    print cmd
    os.system(cmd)

    cmd = "ngram -lm %s -order 2 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
              % (mixed_lm_pg,
                 final_lm_bg)
    print cmd
    os.system(cmd)

    cmd = "cat %s | grep -v '\-pau\-' | grep -v '<s>' | grep -v '</s>' | grep -v '<unk>' | grep -v 'CL_' | grep -v '{' > %s" % \
          (mixed_lm_vocab,
           final_lm_vocab)
    print cmd
    os.system(cmd)

    cmd = """
    echo "<s>	[] sil" > {dict} &&
    echo "</s>	[] sil" >> {dict} &&
    echo "_INHALE_	_inhale_" >> {dict} &&
    echo "_LAUGH_	_laugh_" >> {dict} &&
    echo "_EHM_HMM_	_ehm_hmm_" >> {dict} &&
    echo "_NOISE_	_noise_" >> {dict} &&
    echo "DONE"
    """.format(dict=final_lm_dict)

    print cmd
    os.system(cmd)

    cmd = "perl ../../../tools/htk/bin/PhoneticTranscriptionCS.pl %s %s" % \
          (final_lm_vocab,
           final_lm_dict)
    print cmd
    os.system(cmd)

    cmd = "perl ../../../tools/htk/bin/AddSp.pl %s 1 > %s " % \
          (final_lm_dict,
          final_lm_dict_sp_sil)
    print cmd
    os.system(cmd)

###############################################################################################
print
print "Test language models"

print "-"*120
print "Indomain class-based dev 5-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -order 5 -ppl %s" % (indomain_data_text_dev_norm_cls_pg_arpa,
                                                         indomain_data_text_dev_norm_cls_classes,
                                                         indomain_data_text_dev_norm))
print


print "-"*120
print "Indomain class-based trn 5-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -order 5 -ppl %s" % (indomain_data_text_trn_norm_cls_pg_arpa,
                                                         indomain_data_text_trn_norm_cls_classes,
                                                         indomain_data_text_dev_norm))
print


print "-"*120
print "Extended class-based trn 5-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -classes %s -order 5 -ppl %s" % (extended_data_text_trn_norm_cls_pg_arpa_filtered,
                                                         extended_data_text_trn_norm_cls_classes,
                                                         indomain_data_text_dev_norm))
print


print "-"*120
print "Full trn 5-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -order 5 -ppl %s" % (indomain_data_text_trn_norm_pg_arpa, indomain_data_text_dev_norm))
print


print "-"*120
print "Mixed trn 5-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -order 5 -ppl %s" % (mixed_lm_pg, indomain_data_text_dev_norm))
print

print "-"*120
print "Final 5-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -order 5 -ppl %s" % (final_lm_pg, indomain_data_text_dev_norm))
print


print "-"*120
print "Final 4-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -order 4 -ppl %s" % (final_lm_qg, indomain_data_text_dev_norm))
print


print "-"*120
print "Final 3-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -ppl %s" % (final_lm_tg, indomain_data_text_dev_norm))
print


print "-"*120
print "Final 2-gram LM on dev in-domain data."
print "-"*120
os.system("ngram -lm %s -ppl %s" % (final_lm_bg, indomain_data_text_dev_norm))
print

