#!/bin/bash
# Take the best TIMIT monophone models and reestimate using the
# forced aligned phone transcriptions of WSJ0.
#
# Parameters:
#  $1 - "flat" if we are flat starting from monophone models living
#       in hmm5 in this directory.

cd $WORK_DIR

# Cleanup old files and directories
rm -f -r hmm6 hmm7 hmm8 hmm9
mkdir hmm6 hmm7 hmm8 hmm9

# We'll create a new variance floor macro that reflects 1% of the 
# global variance over our WSJ0 + WSJ1 training data.

# First convert to text format so we can edit the macro file
mkdir -p $WORK_DIR/hmm5_text
HHEd -H $WORK_DIR/hmm5/hmmdefs -H $WORK_DIR/hmm5/macros -M $WORK_DIR/hmm5_text /dev/null $WORK_DIR/config/monophones1

# HCompV parameters:
#  -C   Config file to load, gets us the TARGETKIND = MFCC_0_D_A_Z
#  -f   Create variance floor equal to value times global variance
#  -m   Update the means as well (not needed?)
#  -S   File listing all the feature vector files
#  -M   Where to store the output files
#  -I   MLF containg phone labels of feature vector files
HCompV -A -T 1 -C $TRAIN_COMMON/config -f 0.01 -m -S $WORK_DIR/train.scp -M $WORK_DIR/hmm5_text -I $WORK_DIR/aligned2.mlf $WORK_DIR/config/proto > $LOG_DIR/hcompv.log
cp $WORK_DIR/config/macros $WORK_DIR/hmm5_text/macros
cat $WORK_DIR/hmm5_text/vFloors >> $WORK_DIR/hmm5_text/macros

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm5_text hmm6 config/monophones1 aligned2.mlf 3
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm6 hmm7 config/monophones1 aligned2.mlf 3
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm7 hmm8 config/monophones1 aligned2.mlf 3

# Do an extra round just so we end up with hmm9 and synced with the 
# tutorial.
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm8 hmm9 config/monophones1 aligned2.mlf 3
