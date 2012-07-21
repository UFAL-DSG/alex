#!/bin/bash
# Mixup the number of Gaussians per state, from 1 up to 8.
# We do this in 4 steps, with 4 rounds of reestimation 
# each time.  We mix to 8 to match paper "Large Vocabulary
# Continuous Speech Recognition Using HTK"
#
# Also per Phil Woodland's comment in the mailing list, we
# will let the sp/sil model have double the number of 
# Gaussians.
#
# This version does sil mixup to 2 first, then from 2->4->6->8 for
# normal and double for sil.

cd $WORK_DIR

# Prepare new directories for all our model files
rm -f -r hmm18 hmm19 hmm20 hmm21 hmm22 hmm23 hmm24 hmm25 hmm26 hmm27 hmm28 hmm29 hmm30 hmm31 hmm32 hmm33 hmm34 hmm35 hmm36 hmm37 hmm38 hmm39 hmm40 hmm41 hmm42
mkdir hmm18 hmm19 hmm20 hmm21 hmm22 hmm23 hmm24 hmm25 hmm26 hmm27 hmm28 hmm29 hmm30 hmm31 hmm32 hmm33 hmm34 hmm35 hmm36 hmm37 hmm38 hmm39 hmm40 hmm41 hmm42

# HERest parameters:
#  -d    Where to look for the monophone defintions in
#  -C    Config file to load
#  -I    MLF containing the phone-level transcriptions
#  -t    Set pruning threshold (3.2.1)
#  -S    List of feature vector files
#  -H    Load this HMM macro definition file
#  -M    Store output in this directory
#  -m    Minimum examples needed to update model

# As per the CSTIT notes, do four rounds of reestimation (more than
# in the tutorial).

#######################################################
# Mixup sil from 1->2
HHEd -B -H $WORK_DIR/hmm17/macros -H $WORK_DIR/hmm17/hmmdefs -M $WORK_DIR/hmm18 $TRAIN_COMMON/mix1.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix1.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm18 hmm19 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm19 hmm20 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm20 hmm21 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm21 hmm22 tiedlist wintri.mlf 0

#######################################################
# Mixup 1->2, sil 2->4
HHEd -B -H $WORK_DIR/hmm22/macros -H $WORK_DIR/hmm22/hmmdefs -M $WORK_DIR/hmm23 $TRAIN_COMMON/mix2.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix2.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm23 hmm24 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm24 hmm25 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm25 hmm26 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm26 hmm27 tiedlist wintri.mlf 0

#######################################################
# Mixup 2->4, sil from 4->8
HHEd -B -H $WORK_DIR/hmm27/macros -H $WORK_DIR/hmm27/hmmdefs -M $WORK_DIR/hmm28 $TRAIN_COMMON/mix4.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix4.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm28 hmm29 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm29 hmm30 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm30 hmm31 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm31 hmm32 tiedlist wintri.mlf 0

#######################################################
# Mixup 4->6, sil 8->12
HHEd -B -H $WORK_DIR/hmm32/macros -H $WORK_DIR/hmm32/hmmdefs -M $WORK_DIR/hmm33 $TRAIN_COMMON/mix6.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix6.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm33 hmm34 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm34 hmm35 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm35 hmm36 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm36 hmm37 tiedlist wintri.mlf 0

#######################################################
# Mixup 6->8, sil 12->16
HHEd -B -H $WORK_DIR/hmm37/macros -H $WORK_DIR/hmm37/hmmdefs -M $WORK_DIR/hmm38 $TRAIN_COMMON/mix8.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix8.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm38 hmm39 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm39 hmm40 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm40 hmm41 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm41 hmm42 tiedlist wintri.mlf 0

#######################################################
# Mixup 8->10, sil 16->20
HHEd -B -H $WORK_DIR/hmm42/macros -H $WORK_DIR/hmm42/hmmdefs -M $WORK_DIR/hmm43 $TRAIN_COMMON/mix10.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix10.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm42 hmm43 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm43 hmm44 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm44 hmm45 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm45 hmm46 tiedlist wintri.mlf 0

#######################################################
# Mixup 10->12, sil 20->24
HHEd -B -H $WORK_DIR/hmm46/macros -H $WORK_DIR/hmm46/hmmdefs -M $WORK_DIR/hmm47 $TRAIN_COMMON/mix12.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix12.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm46 hmm47 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm47 hmm48 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm48 hmm49 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm49 hmm50 tiedlist wintri.mlf 0

#######################################################
# Mixup 12->14, sil 24->28
HHEd -B -H $WORK_DIR/hmm50/macros -H $WORK_DIR/hmm50/hmmdefs -M $WORK_DIR/hmm51 $TRAIN_COMMON/mix14.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix14.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm50 hmm51 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm51 hmm52 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm52 hmm53 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm53 hmm54 tiedlist wintri.mlf 0

#######################################################
# Mixup 14->16, sil 28->32
HHEd -B -H $WORK_DIR/hmm54/macros -H $WORK_DIR/hmm54/hmmdefs -M $WORK_DIR/hmm55 $TRAIN_COMMON/mix16.hed $WORK_DIR/tiedlist > $LOG_DIR/hhed_mix16.log

$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm54 hmm55 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm55 hmm56 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm56 hmm57 tiedlist wintri.mlf 0
$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm57 hmm58 tiedlist wintri.mlf 0
