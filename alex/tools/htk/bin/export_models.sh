#!/bin/bash
# Export HMM models for use with Julius.
#
# Parameters:
#  1 - Directory name of model to be exported
#  2 - "text" if models should be converted to text format before running mkbinhmm
#  	   (This may be needed if mkbinhmm would crash otherwise.)

# DEBUG
set -e 

rm -f -r $WORK_DIR/export_models
mkdir $WORK_DIR/export_models

# copy the original models
cp $WORK_DIR/$1/hmmdefs $WORK_DIR/export_models
cp $WORK_DIR/fulllist $WORK_DIR/export_models
cp $WORK_DIR/tiedlist $WORK_DIR/export_models
cp $WORK_DIR/trees $WORK_DIR/export_models
cp $TRAIN_COMMON/config $WORK_DIR/export_models
cp $WORK_DIR/config/monophones1 $WORK_DIR/export_models

# Convert binary models to text models to prevent crashing of mkbinhmm.
# Recipe taken from 
# http://nshmyrev.blogspot.cz/2009/09/using-htk-models-in-sphinx4.html.
if [ "$2" = "text" ]; then
	mkdir $TEMP_DIR/out
	touch $TEMP_DIR/empty
	HHEd -H $WORK_DIR/$1/hmmdefs -H $WORK_DIR/$1/macros -M $TEMP_DIR/out $TEMP_DIR/empty $WORK_DIR/export_models/tiedlist
	mv $TEMP_DIR/out/* $WORK_DIR/export_models/
	rmdir $TEMP_DIR/out
	rm $TEMP_DIR/empty
fi
