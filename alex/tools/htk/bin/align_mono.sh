#!/bin/bash
# Aligns a new MLF based on the best monophone models.
#

# Do alignment using our best monophone models to create a phone-level MLF
# HVite parameters
#  -l       Path to use in the names in the output MLF
#  -o SWT   How to output labels, S remove scores,
#           W do not include words, T do not include times
#  -b       Use this word as the sentence boundary during alignment
#  -C       Config files
#  -a       Perform alignment
#  -H       HMM macro definition files
#  -i       Output to this MLF file
#  -m       During recognition keep track of model boundaries
#  -t       Enable beam searching
#  -y       Extension for output label files
#  -I       Word level MLF file
#  -S       File contain the list of MFC files

HVite -A -T 1 -o SW -b "<s>" -C $TRAIN_COMMON/config -a -H $WORK_DIR/hmm9/macros -H $WORK_DIR/hmm9/hmmdefs -i $WORK_DIR/aligned_mono.mlf -m -t 150.0 -I $WORK_DIR/train_words.mlf -S $WORK_DIR/train.scp $WORK_DIR/dict_train_sp_sil $WORK_DIR/config/monophones1 > $LOG_DIR/hvite_align.log

