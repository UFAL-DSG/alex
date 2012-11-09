#!/bin/bash
#
# Given the CMU 0.7d pronunciation dictionary, convert it
# into the form we'll be using with the HTK.
#
# Also adds in extra words we discovered we needed.

perl $TRAIN_SCRIPTS/FixCMUDict.pl $TRAIN_COMMON/cmudict.0.7a > $TEMP_DIR/cmu_temp

perl $TRAIN_SCRIPTS/FixCMUDict.pl $TRAIN_COMMON/cmudict.ext > $TEMP_DIR/cmu_ext_temp

perl $TRAIN_SCRIPTS/MergeDict.pl $TEMP_DIR/cmu_temp $TEMP_DIR/cmu_ext_temp > $WORK_DIR/dict_full

# # Clean up.
# rm -f $TEMP_DIR/cmu_{,ext_}temp
