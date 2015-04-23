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
if __name__ == '__main__':
    import autopath

import os
import xml.dom.minidom
import glob
import codecs
import random


import alex.corpustools.lm as lm
import alex.utils.various as various

from alex.corpustools.text_norm_cs import normalise_text, exclude_lm
from alex.corpustools.wavaskey import save_wavaskey

def is_srilm_available():
    """Test whether SRILM is available in PATH."""
    return os.system("which ngram-count") == 0


def require_srilm():
    """Test whether SRILM is available in PATH, try to import it from env
    variable and exit the program in case there are problems with it."""
    if not is_srilm_available():
        if 'SRILM_PATH' in os.environ:
            srilm_path = os.environ['SRILM_PATH']
            os.environ['PATH'] += ':%s' % srilm_path
            if not is_srilm_available():
                print 'SRILM_PATH you specified does not contain the ' \
                      'utilities needed. Please make sure you point to the ' \
                      'directory with the SRILM binaries.'
                exit(1)

        else:
            print 'SRILM not found. Set SRILM_PATH environment variable to ' \
                  'the path with SRILM binaries.'
            exit(1)


def exit_on_system_fail(cmd, msg=None):
    system_res = os.system(cmd)
    if not system_res == 0:
        err_msg = "Command failed, exitting."
        if msg:
            err_msg = "%s %s" % (err_msg, msg, )
        raise Exception(err_msg)


if __name__ == '__main__':

    # Test if SRILM is available.
    require_srilm()

    train_data_size                 = 0.90
    bootstrap_text                  = "bootstrap.txt"
    classes                         = "../data/database_SRILM_classes.txt"
    indomain_data_dir               = "indomain_data"
    gen_data                        = lm.download_general_LM_data('cs')

    fn_pt_trn                       = "reference_transcription_trn.txt"
    fn_pt_dev                       = "reference_transcription_dev.txt"

    gen_data_norm                   = '01_gen_data_norm.txt.gz'

    indomain_data_text_trn                              = "04_indomain_data_trn.txt"
    indomain_data_text_trn_norm                         = "04_indomain_data_trn_norm.txt"

    indomain_data_text_dev                              = "05_indomain_data_dev.txt"
    indomain_data_text_dev_norm                         = "05_indomain_data_dev_norm.txt"

    indomain_data_text_trn_norm_vocab                   = "06_indomain_data_trn_norm.txt.vocab"
    indomain_data_text_trn_norm_count1                  = "06_indomain_data_trn_norm.txt.count1"
    indomain_data_text_trn_norm_pg_arpa                 = "06_indomain_data_trn_norm.txt.pg.arpa"

    indomain_data_text_trn_norm_cls                     = "07_indomain_data_trn_norm_cls.txt"
    indomain_data_text_trn_norm_cls_classes             = "07_indomain_data_trn_norm_cls.classes"
    indomain_data_text_trn_norm_cls_vocab               = "07_indomain_data_trn_norm_cls.vocab"
    indomain_data_text_trn_norm_cls_count1              = "07_indomain_data_trn_norm_cls.count1"
    indomain_data_text_trn_norm_cls_pg_arpa             = "07_indomain_data_trn_norm_cls.pg.arpa"

    indomain_data_text_trn_norm_cls_pg_arpa_scoring     = "10_indomain_data_trn_norm_cls.pg.arpa.gen_scoring.gz"

    gen_data_norm_selected                              = '11_gen_data_norm.selected.txt'

    extended_data_text_trn_norm                         = "20_extended_data_trn_norm.txt"
    extended_data_text_trn_norm_cls                     = "20_extended_data_trn_norm_cls.txt"
    extended_data_text_trn_norm_cls_classes             = "20_extended_data_trn_norm_cls.classes"
    extended_data_text_trn_norm_cls_vocab               = "20_extended_data_trn_norm_cls.vocab"
    extended_data_text_trn_norm_cls_count1              = "20_extended_data_trn_norm_cls.count1"
    extended_data_text_trn_norm_cls_pg_arpa             = "20_extended_data_trn_norm_cls.pg.arpa"
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
        exit_on_system_fail(cmd)

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
        pt = []
        for fn in files:
#            print "Processing:", fn
            doc = xml.dom.minidom.parse(fn)
            turns = doc.getElementsByTagName("turn")
            
            for turn in turns:
                recs_list = turn.getElementsByTagName("rec")
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

                    wav_file = recs_list[0].getAttribute('fname')
                    wav_path = os.path.realpath(os.path.join(os.path.dirname(fn), wav_file))

                    pt.append((wav_path, t))

        random.seed(10)
        sf = [(a, b) for a, b in zip(tt, pt)]
        random.shuffle(sf)

        sf_train = sorted(sf[:int(train_data_size*len(sf))], key=lambda k: k[1][0])
        sf_dev = sorted(sf[int(train_data_size*len(sf)):], key=lambda k: k[1][0])

        t_train = [a for a, b in sf_train]
        pt_train = [b for a, b in sf_train]

        t_dev = [a for a, b in sf_dev]
        pt_dev = [b for a, b in sf_dev]

        with codecs.open(indomain_data_text_trn,"w", "UTF-8") as w:
            w.write('\n'.join(t_train))
        with codecs.open(indomain_data_text_dev,"w", "UTF-8") as w:
            w.write('\n'.join(t_dev))

        save_wavaskey(fn_pt_trn, dict(pt_train))
        save_wavaskey(fn_pt_dev, dict(pt_dev))

        # train data
        cmd = r"cat %s %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]_]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % \
              (bootstrap_text,
               indomain_data_text_trn,
               "'",
               indomain_data_text_trn_norm)

        print cmd
        exit_on_system_fail(cmd)

        # dev data
        cmd = r"cat %s | iconv -f UTF-8 -t UTF-8//IGNORE | sed 's/\. /\n/g' | sed 's/[[:digit:]]/ /g; s/[^[:alnum:]_]/ /g; s/[ˇ]/ /g; s/ \+/ /g' | sed 's/[[:lower:]]*/\U&/g' | sed s/[\%s→€…│]//g > %s" % \
              (indomain_data_text_dev,
              "'",
              indomain_data_text_dev_norm)
        print cmd
        exit_on_system_fail(cmd)

    if not os.path.exists(indomain_data_text_trn_norm_cls_pg_arpa):
        print "Generating class-based 5-gram language model from trn in-domain data"
        print "-"*120
        ###############################################################################################
        # convert surface forms to classes
        cmd = r"[ -e %s ] && replace-words-with-classes addone=10 normalize=1 outfile=%s classes=%s %s > %s || exit 1" % \
              (classes,
               indomain_data_text_trn_norm_cls_classes,
               classes,
               indomain_data_text_trn_norm,
               indomain_data_text_trn_norm_cls)

        print cmd
        exit_on_system_fail(cmd, "Maybe you forgot to run "
                                 "'../data/database.py build'?")

        cmd = "ngram-count -text %s -write-vocab %s -write1 %s -order 5 -wbdiscount -memuse -lm %s" % \
              (indomain_data_text_trn_norm_cls,
               indomain_data_text_trn_norm_cls_vocab,
               indomain_data_text_trn_norm_cls_count1,
               indomain_data_text_trn_norm_cls_pg_arpa)

        print cmd
        exit_on_system_fail(cmd)

    if not os.path.exists(indomain_data_text_trn_norm_pg_arpa):
        print
        print "Generating full 5-gram in-domain language model from in-domain data"
        print "-"*120
        cmd = "ngram-count -text %s -write-vocab %s -write1 %s -order 5 -wbdiscount -memuse -lm %s" % \
              (indomain_data_text_trn_norm,
               indomain_data_text_trn_norm_vocab,
               indomain_data_text_trn_norm_count1,
               indomain_data_text_trn_norm_pg_arpa)

        print cmd
        exit_on_system_fail(cmd)

    if not os.path.exists(indomain_data_text_trn_norm_cls_pg_arpa_scoring):
        print
        print "Scoring general text data using the in-domain language model"
        print "-"*120
        ###############################################################################################
        exit_on_system_fail("ngram -lm %s -classes %s -order 5 -debug 1 -ppl %s | gzip > %s" % \
                  (indomain_data_text_trn_norm_cls_pg_arpa,
                   indomain_data_text_trn_norm_cls_classes,
                   gen_data_norm,
                   indomain_data_text_trn_norm_cls_pg_arpa_scoring))

    if not os.path.exists(gen_data_norm_selected):
        print
        print "Selecting similar sentences to in-domain data from general text data"
        print "-"*120
        ###############################################################################################
        exit_on_system_fail("zcat %s | ../../../corpustools/srilm_ppl_filter.py > %s " % (indomain_data_text_trn_norm_cls_pg_arpa_scoring, gen_data_norm_selected))


    if not os.path.exists(extended_data_text_trn_norm_cls_pg_arpa):
        print
        print "Training the in-domain model on the extended data"
        print "-"*120
        ###############################################################################################
        cmd = r"cat %s %s > %s" % (indomain_data_text_trn_norm, gen_data_norm_selected, extended_data_text_trn_norm)
        # cmd = r"cat %s > %s" % (indomain_data_text_trn_norm, extended_data_text_trn_norm)
        print cmd
        exit_on_system_fail(cmd)

        # convert surface forms to classes
        cmd = r"[ -e %s ] && replace-words-with-classes addone=10 normalize=1 outfile=%s classes=%s %s > %s || exit 1" % \
              (classes,
               extended_data_text_trn_norm_cls_classes,
               classes,
               extended_data_text_trn_norm,
               extended_data_text_trn_norm_cls)

        print cmd
        exit_on_system_fail(cmd, "Maybe you forgot to run "
                                 "'../data/database.py build'?")

        cmd = "ngram-count -text %s -vocab %s -limit-vocab -write-vocab %s -write1 %s -order 5 -wbdiscount -memuse -lm %s" % \
              (extended_data_text_trn_norm_cls,
               indomain_data_text_trn_norm_cls_vocab,
               extended_data_text_trn_norm_cls_vocab,
               extended_data_text_trn_norm_cls_count1,
               extended_data_text_trn_norm_cls_pg_arpa)

        print cmd
        exit_on_system_fail(cmd)

        cmd = "cat %s | grep -v 'CL_[[:alnum:]_]\+[[:alnum:] _]\+CL_'> %s" % \
              (extended_data_text_trn_norm_cls_pg_arpa,
               extended_data_text_trn_norm_cls_pg_arpa_filtered)

        print cmd
        exit_on_system_fail(cmd)

        cmd = "ngram -lm %s -order 5 -write-lm %s -renorm" % \
              (extended_data_text_trn_norm_cls_pg_arpa_filtered,
               extended_data_text_trn_norm_cls_pg_arpa_filtered)

        print cmd
        exit_on_system_fail(cmd)

    if not os.path.exists(expanded_lm_pg):
        print
        print "Expanding the language model"
        print "-"*120
        ###############################################################################################

        cmd = "ngram -lm %s -classes %s -order 5 -expand-classes 5 -write-vocab %s -write-lm %s -prune 0.0000001 -renorm" \
                  % (extended_data_text_trn_norm_cls_pg_arpa_filtered,
                     extended_data_text_trn_norm_cls_classes,
                     expanded_lm_vocab,
                     expanded_lm_pg)
        print cmd
        exit_on_system_fail(cmd)

    if not os.path.exists(mixed_lm_pg):
        print
        print "Mixing the expanded class-based model and the full model"
        print "-"*120
        ###############################################################################################

        cmd = "ngram -lm %s -mix-lm %s -lambda %s -order 5 -write-vocab %s -write-lm %s -prune 0.00000001 -renorm" \
                  % (expanded_lm_pg,
                     indomain_data_text_trn_norm_pg_arpa,
                     mixing_weight,
                     mixed_lm_vocab,
                     mixed_lm_pg)
        print cmd
        exit_on_system_fail(cmd)

    if not os.path.exists(final_lm_pg):
        print
        print "Building the final language models"
        print "-"*120
        ###############################################################################################

        cmd = "ngram -lm %s -order 5 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
                  % (mixed_lm_pg,
                     final_lm_pg)
        print cmd
        exit_on_system_fail(cmd)

        cmd = "ngram -lm %s -order 4 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
                  % (mixed_lm_pg,
                     final_lm_qg)
        print cmd
        exit_on_system_fail(cmd)

        cmd = "ngram -lm %s -order 3 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
                  % (mixed_lm_pg,
                     final_lm_tg)
        print cmd
        exit_on_system_fail(cmd)

        cmd = "ngram -lm %s -order 2 -write-lm %s -prune-lowprobs -prune 0.0000001 -renorm" \
                  % (mixed_lm_pg,
                     final_lm_bg)
        print cmd
        exit_on_system_fail(cmd)

        cmd = "cat %s | grep -v '\-pau\-' | grep -v '<s>' | grep -v '</s>' | grep -v '<unk>' | grep -v 'CL_' | grep -v '{' | grep -v '_' > %s" % \
              (mixed_lm_vocab,
               final_lm_vocab)
        print cmd
        exit_on_system_fail(cmd)

        cmd = "echo '' > {dict}".format(dict=final_lm_dict)
        print cmd
        exit_on_system_fail(cmd)

        cmd = "perl ../../../tools/htk/bin/PhoneticTranscriptionCS.pl %s %s" % \
              (final_lm_vocab,
               final_lm_dict)
        print cmd
        exit_on_system_fail(cmd)


###############################################################################################
    print
    print "Test language models"

    print "-"*120
    print "Class-based trn 5-gram LM on trn data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -classes %s -order 5 -ppl %s" % (indomain_data_text_trn_norm_cls_pg_arpa,
                                                             indomain_data_text_trn_norm_cls_classes,
                                                             indomain_data_text_trn_norm))
    print

    print "-"*120
    print "Full trn 5-gram LM on trn data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (indomain_data_text_trn_norm_pg_arpa, indomain_data_text_trn_norm))
    print
    print


    print "-"*120
    print "Class-based trn 5-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -classes %s -order 5 -ppl %s -zeroprob-word _NOISE_" % (indomain_data_text_trn_norm_cls_pg_arpa,
                                                             indomain_data_text_trn_norm_cls_classes,
                                                             indomain_data_text_dev_norm))
    print


    print "-"*120
    print "Extended class-based trn 5-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -classes %s -order 5 -ppl %s -zeroprob-word _NOISE_" % (extended_data_text_trn_norm_cls_pg_arpa,
                                                             extended_data_text_trn_norm_cls_classes,
                                                             indomain_data_text_dev_norm))
    print


    print "-"*120
    print "Extended filtered class-based trn 5-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -classes %s -order 5 -ppl %s -zeroprob-word _NOISE_" % (extended_data_text_trn_norm_cls_pg_arpa_filtered,
                                                             extended_data_text_trn_norm_cls_classes,
                                                             indomain_data_text_dev_norm))
    print


    print "-"*120
    print "Expanded class-based trn 5-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -order 5 -ppl %s -zeroprob-word _NOISE_" % (expanded_lm_pg, indomain_data_text_dev_norm))
    print

    print "-"*120
    print "Full trn 5-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (indomain_data_text_trn_norm_pg_arpa, indomain_data_text_dev_norm))
    print


    print "-"*120
    print "Mixed trn 5-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (mixed_lm_pg, indomain_data_text_dev_norm))
    print

    print "-"*120
    print "Final 5-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (final_lm_pg, indomain_data_text_dev_norm))
    print


    print "-"*120
    print "Final 4-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -order 4 -ppl %s" % (final_lm_qg, indomain_data_text_dev_norm))
    print


    print "-"*120
    print "Final 3-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -ppl %s" % (final_lm_tg, indomain_data_text_dev_norm))
    print


    print "-"*120
    print "Final 2-gram LM on dev data."
    print "-"*120
    exit_on_system_fail("ngram -lm %s -ppl %s" % (final_lm_bg, indomain_data_text_dev_norm))
    print
