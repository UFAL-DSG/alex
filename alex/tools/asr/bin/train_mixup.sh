#!/bin/bash
# Mix up the number of Gaussians per state, from 1 up to 8.
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

# Prepare new directories for all our model files.
for num in `seq 18 67`; do
	rm -rf hmm$num
	mkdir hmm$num
done

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

# Gradually add 2 Gaussians to regular phone HMMs' states and 4 Gaussians 
# to the silence model and re-estimate, until 18 Gaussians per state are 
# reached.
#
# The resulting models will be in these directories:
#
# 	dir     # Gauss for normal    # Gauss for sil
# 	─────────────────────────────────────────────
# 	hmm32                    4                  8
# 	hmm37                    6                 12
# 	hmm42                    8                 16
# 	hmm47                   10                 20
# 	hmm52                   12                 24
# 	hmm57                   14                 28
# 	hmm62                   16                 32
# 	hmm67                   18                 36

n_iters=4  # number of re-estimation iterations
					 # (The table above assumes this is 4.)
step_size=2  # number of Gaussians added to normal phone models in each step
						 # (The table above assumes this is 2.)

for new_n in `seq 4 $step_size 18`; do
	# Split off the new Gaussians.
	hmm_idx=$(($new_n / $step_size * $(($n_iters + 1)) + 18))
	prev_dir="$WORK_DIR/hmm$(($hmm_idx - 1))"
	HHEd -B -H $prev_dir/macros -H $prev_dir/hmmdefs \
		-M $WORK_DIR/hmm$hmm_idx \
		$TRAIN_COMMON/mix$new_n.hed $WORK_DIR/tiedlist \
		>$LOG_DIR/hhed_mix$new_n.log

	# Re-estimate.
	for iter in `seq 0 $(($n_iters - 1))`; do
		$TRAIN_SCRIPTS/train_iter.sh $WORK_DIR hmm$(($hmm_idx + $iter)) \
			hmm$(($hmm_idx + $iter + 1)) tiedlist wintri.mlf 0
	done
done
