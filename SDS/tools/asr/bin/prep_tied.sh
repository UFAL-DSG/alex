#!/bin/bash
# Prepare things for the tied state triphones.
#
# Parameters:
#   1 - RO value for clustering
#   2 - TB value for clustering
#
# We need to create a list of all the triphone contexts we might
# see based on the whole dictionary (not just what we see in
# the training data).

cd $WORK_DIR

rm -f -r hmm13 hhed_cluster.log fullist tree.hed
mkdir hmm13

# We have our own script which generates all possible monophone,
# left and right biphones, and triphones.  It will also add
# an entry for sp and sil.
#if [[ $3 != "cross" ]]
#then
#  perl $TRAIN_SCRIPTS/CreateFullListWI.pl $WORK_DIR/dict_full > $TEMP_DIR/fulllist
#else
#  perl $TRAIN_SCRIPTS/CreateFullList.pl $WORK_DIR/config/monophones1 > $TEMP_DIR/fulllist
#fi
perl $TRAIN_SCRIPTS/CreateFullList.pl $WORK_DIR/config/monophones0 > $TEMP_DIR/fulllist
cat $TEMP_DIR/fulllist triphones1 | sort | uniq > $WORK_DIR/fulllist


# Now create the instructions for doing the decision tree clustering.

# RO sets the outlier threshold and load the stats file from the
# last round of training.
echo "RO $1 stats" > $WORK_DIR/tree.hed

# Add the phonetic questions used in the decision tree.
echo "TR 0" >> $WORK_DIR/tree.hed
cat $WORK_DIR/config/tree_ques.hed >> $WORK_DIR/tree.hed

# Now the commands that cluster each output state.
echo "TR 12" >> $WORK_DIR/tree.hed
perl $TRAIN_SCRIPTS/MakeClusteredTri.pl TB $2 $WORK_DIR/config/monophones1 >> $WORK_DIR/tree.hed

echo "TR 1" >> $WORK_DIR/tree.hed
echo "AU \"fulllist\"" >> $WORK_DIR/tree.hed

echo "CO \"tiedlist\"" >> $WORK_DIR/tree.hed
echo "ST \"trees\"" >> $WORK_DIR/tree.hed

# Do the clustering
HHEd -A -T 1 -H $WORK_DIR/hmm12/macros -H $WORK_DIR/hmm12/hmmdefs -M $WORK_DIR/hmm13 $WORK_DIR/tree.hed $WORK_DIR/triphones1 > $LOG_DIR/hhed_cluster.log

