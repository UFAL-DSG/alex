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

HVite -A -T 1 -o SWT -C $TRAIN_COMMON/config -a -H $WORK_DIR/hmm5/macros -H $WORK_DIR/hmm5/hmmdefs -i $WORK_DIR/aligned.mlf -m -t 150.0 -I $WORK_DIR/train_words.mlf -S $WORK_DIR/train.scp $WORK_DIR/dict_train_sp_sil $WORK_DIR/config/monophones1 > $LOG_DIR/hvite_align.log

# We'll get a "sp sil" sequence at the end of each sentance.  Merge these
# into a single sil phone.  Also might get "sil sil", we'll merge anything
# combination of sp and sil into a single sil.
HLEd -A -T 1 -i $WORK_DIR/aligned2.mlf $TRAIN_COMMON/merge_sp_sil.led $WORK_DIR/aligned.mlf > $LOG_DIR/hled_sp_sil.log

# Forced alignment might fail for a few files (why?), these will be missing
# from the MLF, so we need to prune these out of the script so we don't try
# and train on them.
cp $WORK_DIR/train.scp $WORK_DIR/train_non_pruned.scp
perl $TRAIN_SCRIPTS/RemovePrunedFiles.pl $WORK_DIR/aligned2.mlf $WORK_DIR/train.scp > $WORK_DIR/train_pruned.scp
cp $WORK_DIR/train_pruned.scp $WORK_DIR/train.scp
