#!/bin/bash
# Evaluate on the test set.
#
# During the recognition, we'll output lattices
# for each of the test utterances, this will alow
# us to tune the LM scale factor and insertion
# penalty much quicker than recognizing.
#
# Parameters:
#  1 - Directory name of model to test
#  2 - Distinguishing name for this test run.
#  3 - HVite pruning value
#  4 - Insertion penalty
#  5 - Language model scale factor
#  6 - Language model
#  7 - Dictionary

cd $WORK_DIR

# HVite parameters:
#  -H    HMM macro definition files to load
#  -S    List of feature vector files to recognize
#  -i    Where to output the recognition MLF file
#  -w    Word network to you as language model
#  -p    Insertion penalty
#  -s    Language model scale factor
#  -z    Extension for lattice output files
#  -n    Number of tokens in a state (bigger number means bigger lattices)

# We'll run with some reasonable values for insertion penalty and LM scale,
# but these will need to be tuned.

DICT=$7

if [[ $8 != "cross" ]]
then
  HVite -A -T 1 -t $3 -C $TRAIN_COMMON/configwi    -H $WORK_DIR/$1/macros -H $WORK_DIR/$1/hmmdefs -S $WORK_DIR/test.scp -i $WORK_DIR/recout_test_$8_$2.mlf -w $6 -p $4 -s $5 -z lat -n 4 $DICT $WORK_DIR/tiedlist > $LOG_DIR/hvite_test_$8_$2.log
else
  HVite -A -T 1 -t $3 -C $TRAIN_COMMON/configcross -H $WORK_DIR/$1/macros -H $WORK_DIR/$1/hmmdefs -S $WORK_DIR/test.scp -i $WORK_DIR/recout_test_$8_$2.mlf -w $6 -p $4 -s $5 -z lat -n 4 $DICT $WORK_DIR/tiedlist > $LOG_DIR/hvite_test_$8_$2.log
fi


# Now lets see how we did!
HResults -n -A -T 1 -I $WORK_DIR/test_words.mlf $WORK_DIR/tiedlist $WORK_DIR/recout_test$2.mlf > $WORK_DIR/hresults_test$2.log

# Add on a NIST style output result for good measure
HResults -n -h -A -T 1 -I $WORK_DIR/test_words.mlf $WORK_DIR/tiedlist $WORK_DIR/recout_test$2.mlf >> $WORK_DIR/hresults_test$2.log
