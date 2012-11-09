#!/bin/bash

# Train the triphone models

cd $WORK_DIR

rm -f -r hmm11 hmm12 hmm11.log hmm12.log
mkdir hmm11 hmm12

# Also generate stats file we use for state tying.
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm10 hmm11 triphones1 wintri.mlf 1
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm11 hmm12 triphones1 wintri.mlf 1

# Copy the stats file off to the main directory for use in state tying
cp $WORK_DIR/hmm12/stats_hmm12 $WORK_DIR/stats
