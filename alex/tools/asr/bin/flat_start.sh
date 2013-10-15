#!/bin/bash
# If previous monophone models aren't available (say from TIMIT), then
# this script can be used to flat start the models using the word 
# level MLF of WSJ0.

cd $WORK_DIR
rm -f -r hmm0 hmm1 hmm2 hmm3 hmm4 hmm5
mkdir hmm0 hmm1 hmm2 hmm3 hmm4 hmm5

# First convert the word level MLF into a phone MLF
HLEd -A -T 1 -l '*' -d $WORK_DIR/dict_train -i $WORK_DIR/phones0.mlf $TRAIN_COMMON/mkphones0.led $WORK_DIR/train_words.mlf > $LOG_DIR/hled_flat.log

# Compute the global mean and variance and set all Gaussians in the given
# HMM to have the same mean and variance

# HCompV parameters:
#  -C   Config file to load, gets us the TARGETKIND = MFCC_0_D_A_Z
#  -f   Create variance floor equal to value times global variance
#  -m   Update the means as well
#  -S   File listing all the feature vector files
#  -M   Where to store the output files
HCompV -A -T 1 -C $TRAIN_COMMON/config -f 0.01 -m -S $WORK_DIR/train.scp -M $WORK_DIR/hmm0 $WORK_DIR/config/proto > $LOG_DIR/hcompv_flat.log

# Create the master model definition and macros file.
cp $WORK_DIR/config/macros $WORK_DIR/hmm0
cat $WORK_DIR/hmm0/vFloors >> $WORK_DIR/hmm0/macros
perl $TRAIN_SCRIPTS/CreateHMMDefs.pl $WORK_DIR/hmm0/proto $WORK_DIR/config/monophones0 > $WORK_DIR/hmm0/hmmdefs

# Okay now to train up the models
#
# HERest parameters:
#  -d    Where to look for the monophone defintions in
#  -C    Config file to load
#  -I    MLF containing the phone-level transcriptions
#  -t    Set pruning threshold (3.2.1)
#  -S    List of feature vector files
#  -H    Load this HMM macro definition file
#  -M    Store output in this directory
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm0 hmm1 config/monophones0 phones0.mlf 3 text
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm1 hmm2 config/monophones0 phones0.mlf 3 text
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm2 hmm3 config/monophones0 phones0.mlf 3 text

# Finally we'll fix the silence model and add in our short pause sp 
# See HTKBook 3.2.2.
perl $TRAIN_SCRIPTS/DuplicateSilence.pl $WORK_DIR/hmm3/hmmdefs > $WORK_DIR/hmm4/hmmdefs
cp $WORK_DIR/hmm3/macros $WORK_DIR/hmm4/macros

HHEd -A -T 1 -H $WORK_DIR/hmm4/macros -H $WORK_DIR/hmm4/hmmdefs -M $WORK_DIR/hmm5 $TRAIN_COMMON/sil.hed $WORK_DIR/config/monophones1 > $LOG_DIR/hhed_flat_sil.log
