#!/usr/bin/env python
# encoding: utf-8
"""
Building LM with irstlm
"""
from __future__ import division, unicode_literals
from subprocess import call
import os
from os.path import isfile

if __name__ == '__main__':
    import autopath

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

norm_data = "input.txt"
classes = "../data/database_SRILM_classes.txt"
indomain_data_text_trn_norm_cls_classes             = "07_indomain_data_trn_norm_cls.classes"
norm_data_class = "normalized_with_classes"
norm_data_class_se = "normalized_with_classes_se"
class_ngrams_n = 3
class_ngrams = "class_ngram_counts"
norm_data_ngrams_estim_classes = "norm_data_ngrams_estim_classes"
class_arpa = "class_arpa"
norm_data_se = norm_data + '_se'
######################### script start #############################

if (not isfile(indomain_data_text_trn_norm_cls_classes)) or (not isfile(norm_data_class)):
    replace_with_classes_main(norm_data, classes,
            indomain_data_text_trn_norm_cls_classes, norm_data_class, add_n_smoothing=0, counts_only=True)

if not isfile(norm_data_class_se):
    s('cat %s | add-start-end.sh > %s' % (norm_data_class, norm_data_class_se))

if not isfile(class_ngrams):
    s('ngt -i=%s -n=%d, -o=%s' % (norm_data_class_se, class_ngrams_n, class_ngrams))

if not isfile(norm_data_ngrams_estim_classes):
    ngrams_discard_classes(class_ngrams, class_ngrams_n, indomain_data_text_trn_norm_cls_classes, norm_data_ngrams_estim_classes, force_integer_counts=True, class_smooth=10)

if not isfile(class_arpa):
    print 'debug 0'
    s('tlm -tr=%s -n=%d -lm=LinearWittenBell -oarpa=%s' % (class_ngrams, class_ngrams_n, class_arpa))
    print '\ndebug 1'
    # s('tlm -tr=%s -n=%d -lm=LinearWittenBell -oarpa=%s' % (norm_data_ngrams_estim_classes, class_ngrams_n, class_arpa))


# # perplexity on the training data
# if not isfile(norm_data_se):
#     s('cat %s | add-start-end.sh > %s' % (norm_data, norm_data_se))
# s('compile-lm %s --eval=%s' % (class_arpa, norm_data_se))
