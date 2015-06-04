#!/usr/bin/env python
# encoding: utf-8
"""
Building LM with irstlm
"""
from __future__ import division, unicode_literals
from subprocess import call
import os

if __name__ == '__main__':
    import autopath

from alex.corpustools.replace_with_classes import main as replace_with_classes_main


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
output = "normalized_with_classes"
###############################################################################################
# convert surface forms to classes
# TODO in python replace-words-with-classes

if os.path.isfile(classes):
    replace_with_classes_main(norm_data, classes, indomain_data_text_trn_norm_cls_classes, output, add_n_smoothing=10, counts_only=False)


# cmd = r"[ -e %s ] && replace-words-with-classes addone=10 normalize=1 outfile=%s classes=%s %s > %s || exit 1" % \
#       (classes,
#        classes,
#        norm_data,
#        indomain_data_text_trn_norm_cls)
