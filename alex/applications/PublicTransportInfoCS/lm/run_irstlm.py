#!/usr/bin/env python
# encoding: utf-8
"""
Building LM with irstlm
"""
from __future__ import division, unicode_literals
if __name__ == '__main__':
    import autopath

from subprocess import call
import os
from os.path import isfile
from build import exit_on_system_fail


from alex.corpustools.replace_with_classes import main as replace_with_classes_main
from alex.corpustools.ngrams_discard_classes import main as ngrams_discard_classes


def s(shell_cmd):
    """Pass the command without any escaping as one would pass to bash"""
    return call(shell_cmd, shell=True)

def setup_irstlm_env():
    """Test whether IRSLM is available in PATH."""
    if 'IRSTLM' not in os.environ:
        raise Exception('Specify IRSTLM shell variable')
    else:
        os.environ['PATH'] = '%s:%s' % (os.environ['IRSTLM'], os.environ['PATH'])
    call("build-lm.sh")  # test that IRSLM binaries are callable and in PATH
    return

indomain_data_text_trn_norm_cls_classes             = "07_indomain_data_trn_norm_cls.classes"
indomain_data_text_trn_norm_cls_pg_arpa             = "07_indomain_data_trn_norm_cls.pg.arpa"
indomain_data_text_trn_norm_cls_pg_arpa             = "07_indomain_data_trn_norm_cls.pg.arpa"
indomain_data_text_dev_norm                         = "05_indomain_data_dev_norm.txt"
indomain_data_text_trn_norm                         = "04_indomain_data_trn_norm.txt"
indomain_data_text_dev_norm_se = indomain_data_text_dev_norm + '_se'
norm_data = indomain_data_text_trn_norm
norm_data = "input.txt"  # TODO debug
classes = "../data/database_SRILM_classes.txt"
norm_data_class = "normalized_with_classes"
norm_data_class_se = norm_data_class + "_se"
class_ngrams_n = 3
class_ngrams = "class_ngram_counts"
norm_data_ngrams_estim_classes = "norm_data_ngrams_estim_classes"
class_arpa = "class_arpa"
norm_data_se = norm_data + '_se'
plain_ngrams = "plain_ngram_counts"
plain_arpa = "plain_arpa"


######################### script start #############################
print 'Estimating classed based models with expanded classes\n'
if (not isfile(indomain_data_text_trn_norm_cls_classes)) or (not isfile(norm_data_class)):
    replace_with_classes_main(norm_data, classes,
            indomain_data_text_trn_norm_cls_classes, norm_data_class,
            add_n_smoothing=0, counts_only=True)

if not isfile(norm_data_class_se):
    s('cat %s | add-start-end.sh > %s' % (norm_data_class, norm_data_class_se))

if not isfile(class_ngrams):
    s('ngt -i=%s -n=%d, -o=%s' % (norm_data_class_se, class_ngrams_n, class_ngrams))

if not isfile(norm_data_ngrams_estim_classes):
    ngrams_discard_classes(class_ngrams, class_ngrams_n, indomain_data_text_trn_norm_cls_classes, norm_data_ngrams_estim_classes, force_integer_counts=True, class_smooth=10)

if not isfile(class_arpa):
    s('tlm -tr=%s -n=%d -lm=LinearWittenBell -oarpa=%s' % (norm_data_ngrams_estim_classes, class_ngrams_n, class_arpa))


print 'Estimating plain model\n'
if not isfile(norm_data_se):
    s('cat %s | add-start-end.sh > %s' % (norm_data, norm_data_se))
if not isfile(plain_ngrams):
    s('ngt -i=%s -n=%d, -o=%s' % (norm_data_se, class_ngrams_n, plain_ngrams))
if not isfile(plain_arpa):
    s('tlm -tr=%s -n=%d -lm=LinearWittenBell -oarpa=%s' % (plain_ngrams, class_ngrams_n, plain_arpa))

from sys import exit; exit(0)  # TODO debug I have to install SRILM

# perplexity on the training data using IRSTLM
print 'IRSTLM perplexity of plain on trn data'
s('compile-lm %s --eval=%s' % (plain_arpa, norm_data_se))
print 'IRSTLM perplexity of CB LM on trn data'
s('compile-lm %s --eval=%s' % (class_arpa, norm_data_se))


if not isfile(indomain_data_text_dev_norm_se):
    s('cat %s | add-start-end.sh > %s' % (indomain_data_text_dev_norm, indomain_data_text_dev_norm_se))

print 'IRSTLM perplexity of plain on dev data'
s('compile-lm %s --eval=%s' % (plain_arpa, indomain_data_text_dev_norm_se))
print 'IRSTLM perplexity of CB LM on dev data'
s('compile-lm %s --eval=%s' % (class_arpa, indomain_data_text_dev_norm_se))


print "Test language models TODO still using SRILM"

print "-"*120
print "Class-based NEW approach trn 5-gram LM on trn data."
print "-"*120
exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (class_arpa, indomain_data_text_trn_norm))

print "-"*120
print "Class-based NEW approach trn 5-gram LM on dev data."
print "-"*120
exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (class_arpa, indomain_data_text_dev_norm))

print "-"*120
print "Non Class-based trn 5-gram LM on trn data."
print "-"*120
exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (plain_arpa, indomain_data_text_trn_norm))
print "-"*120
print "Non Class-based trn 5-gram LM on dev data."
print "-"*120
exit_on_system_fail("ngram -lm %s -order 5 -ppl %s" % (plain_arpa, indomain_data_text_dev_norm))

print "-"*120
print "Class-based trn 5-gram LM on trn data."
print "-"*120
exit_on_system_fail("ngram -lm %s -classes %s -order 5 -ppl %s" % (indomain_data_text_trn_norm_cls_pg_arpa,
                                                         indomain_data_text_trn_norm_cls_classes,
                                                         indomain_data_text_trn_norm))
print "-"*120
print "Class-based trn 5-gram LM on dev data."
print "-"*120
exit_on_system_fail("ngram -lm %s -classes %s -order 5 -ppl %s -zeroprob-word _NOISE_" % (indomain_data_text_trn_norm_cls_pg_arpa,
                                                         indomain_data_text_trn_norm_cls_classes,
                                                         indomain_data_text_dev_norm))
print



TODO jak zintegrovat lower ngrams, and higher ngrams check format after ngt, ask Nicola what the ngt command do and what the format means
