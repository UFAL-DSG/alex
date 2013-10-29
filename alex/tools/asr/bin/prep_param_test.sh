#!/bin/bash
# This encodes the test data.

cd "$WORK_DIR"

# Create the list file we need to send to HCopy to convert .wav files to .mfc.
WAVMAP="$WORK_DIR"/test_wavs.txt
MFCLST="$WORK_DIR"/test_mfcs.txt
# Find wavs to be coded.
find -L "$TEST_DATA_SOURCE" -iname '*.wav' -printf '%f\t%p\n' \
	| sed -e 's/\.wav\t/\t/' \
	| LC_ALL=C sort -t'	' -k1,1 >"$WAVMAP"
# Find mfcs already present.
find "$TEST_DATA" -maxdepth 1 -iname '*.mfc' -printf '%f\n' \
	| sed -e 's/\.mfc$//' \
	| LC_ALL=C sort >"$MFCLST"
# Discard wavs that already have their mfcs from the list.
cut -d'	' -f1,1 "$WAVMAP" \
	| LC_ALL=C comm -23 - "$MFCLST" >"$TEMP_DIR"/new_wavs.lst
# Join the list of new wavs and the mapping of wavs' basenames to paths.
LC_ALL=C join -t'	' -j1 -o1.2,0 "$WAVMAP" "$TEMP_DIR"/new_wavs.lst \
	| gawk -- 'BEGIN {FS = "\t"; OFS = " "}
							 {print $1, "'"$TEST_DATA"'/" $2 ".mfc"}
						' >"$WORK_DIR"/test_wav_mfc.scp
rm -f "$TEMP_DIR"/new_wavs.lst


HCopy -T 1 -C $TRAIN_COMMON/configwav -C $TRAIN_COMMON/config -S $WORK_DIR/test_wav_mfc.scp > $LOG_DIR/hcopy_test.log
