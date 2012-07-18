#!/bin/bash
# This encodes the test data

cd $TRAIN_DIR

# Create a file with the filename with wav and mfc extensions on it
# Only get the files in the training directory.
find $TEST_DATA_SOURCE -iname '*.wav' > $WORK_DIR/test_wav_files.txt

# Create the list file we need to send to HCopy to convert .wav files to .mfc
perl $TRAIN_SCRIPTS/CreateMFCList.pl $WORK_DIR/test_wav_files.txt wav mfc > $TEMP_DIR/test_wav_mfc.scp
python $TRAIN_SCRIPTS/SubstituteInMFCList.py $TEMP_DIR/test_wav_mfc.scp $TEST_DATA > $WORK_DIR/test_wav_mfc.scp

HCopy -T 1 -C $TRAIN_COMMON/configwav -C $TRAIN_COMMON/config -S test_wav_mfc.scp > $LOG_DIR/hcopy_test.log
