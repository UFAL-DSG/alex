#!/bin/bash
# Export hmm models
#
# Parameters:
#  1 - Directory name of model to be exported

cd $WORK_DIR

rm -f -r export_models
mkdir export_models

# copy the original models
cp $WORK_DIR/$1/hmmdefs $WORK_DIR/export_models
cp $WORK_DIR/fulllist $WORK_DIR/export_models
cp $WORK_DIR/tiedlist $WORK_DIR/export_models
cp $WORK_DIR/trees $WORK_DIR/export_models
cp $TRAIN_COMMON/config $WORK_DIR/export_models
cp $WORK_DIR/config/monophones1 $WORK_DIR/export_models

# create Julius ASR binary AM models
mkbinhmm -htkconf $WORK_DIR/export_models/config $WORK_DIR/export_models/hmmdefs $WORK_DIR/export_models/julius_hmmdefs
mkbinhmmlist $WORK_DIR/export_models/hmmdefs $WORK_DIR/export_models/tiedlist $WORK_DIR/export_models/julius_tiedlist
