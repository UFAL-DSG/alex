#!/bin/bash
# Train the word internal phonetic decision tree state tied models

cd $WORK_DIR

# Cleanup old files and create new directories for model files
rm -f -r hmm14 hmm15 hmm16 hmm17
mkdir hmm14 hmm15 hmm16 hmm17
rm -f

# HERest parameters:
#  -d    Where to look for the monophone definitions in
#  -C    Config file to load
#  -I    MLF containing the phone-level transcriptions
#  -t    Set pruning threshold (3.2.1)
#  -S    List of feature vector files
#  -H    Load this HMM macro definition file
#  -M    Store output in this directory
#  -m    Sets the minimum number of examples for training, by setting
#        to 0 we stop suprious warnings about no examples for the
#        sythensized triphones
#
# As per the CSTIT notes, do four rounds of re-estimation (more than
# in the tutorial).

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm13 hmm14 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm14 hmm15 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm15 hmm16 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm16 hmm17 tiedlist wintri.mlf 0
