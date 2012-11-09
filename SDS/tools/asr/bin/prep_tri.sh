#!/bin/bash
# Convert our monophone models and MLFs into word internal triphones.
#

cd $WORK_DIR

rm -f -r mktri.hed hmm10
mkdir hmm10

# Check to see if we are doing cross word triphones or not.
if [[ $1 != "cross" ]]
then
  # This converts the monophone MLF into a word internal triphone MLF.
  HLEd -A -T 1 -n $WORK_DIR/triphones1 -i $WORK_DIR/wintri.mlf $TRAIN_COMMON/mktri.led $WORK_DIR/aligned2.mlf > $LOG_DIR/hled_make_tri.log
else
  # This version makes it into a cross word triphone MLF, the short pause
  # phone will not block context across words.
  HLEd -A -T 1 -n $WORK_DIR/triphones1 -i $WORK_DIR/wintri.mlf $TRAIN_COMMON/mktri_cross.led aligned2.mlf > $LOG_DIR/hled_make_tri_cross.log
fi


# Prepare the script that will be used to clone the monophones into
# their cooresponding triphones.  The script will also tie the transition
# matrices of all triphones with the same central phone together.
perl $TRAIN_SCRIPTS/MakeClonedMono.pl $WORK_DIR/config/monophones1 $WORK_DIR/triphones1 > $WORK_DIR/mktri.hed

# Go go gadget clone monophones and tie transition matricies
HHEd -A -T 1 -H $WORK_DIR/hmm9/macros -H $WORK_DIR/hmm9/hmmdefs -M $WORK_DIR/hmm10 $WORK_DIR/mktri.hed $WORK_DIR/config/monophones1 > $LOG_DIR/hhed_clone_mono.log
