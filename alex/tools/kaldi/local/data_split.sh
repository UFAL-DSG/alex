#!/bin/bash
# Copyright (c) 2013, Ondrej Platek, Ufal MFF UK <oplatek@ufal.mff.cuni.cz>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
# WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
# MERCHANTABLITY OR NON-INFRINGEMENT.
# See the Apache 2 License for the specific language governing permissions and
# limitations under the License. #
#
# Makes train/test splits
# local/voxforge_data_prep.sh --nspk_test ${nspk_test} ${SELECTED} || exit 1
# create files: (TYPE=train|test)
#   a) ${TYPE}_trans.txt: ID transcription capitalized! No interputction
#   b) ${TYPE}_wav.scp: ID path2ID.wav 
#   c) $TYPE.utt2spk: ID-recording ID-speaker
#   s) $TYPE.spk2utt
#   e) $TYPE.spk2gender  all speakers are male
# we have ID-recording = ID-speaker

# The vystadial data are specific by having following marks in transcriptions
# _INHALE_
# _LAUGH_ 
# _EHM_HMM_ 
# _NOISE_
# _EHM_HMM_
# _SIL_

set -e
# set -x

every_n=1

[ -f path.sh ] && . ./path.sh # source the path.
. utils/parse_options.sh || exit 1;


if [ $# -ne 4 ] ; then
    echo "Usage: $0 [--every-n 30] <data-directory>  <local-directory> <LMs> <Test-Sets>";
    exit 1;
fi

DATA=$1; shift
locdata=$1; shift
LMs=$1; shift
test_sets=$1; shift


echo "LMs $LMs  test_sets $test_sets"


echo "=== Starting initial Vystadial data preparation ..."
echo "--- Making test/train data split from $DATA taking every $every_n recording..."

mkdir -p $locdata



i=0
for s in $test_sets train ; do
  mkdir -p $locdata/$s

  echo "Initializing set '$s' output files"
  for f in spk2utt trans.txt utt2spk wav.scp ; do
    echo -n "" > "$locdata/$s/$f"
  done
  echo -n "" > "$locdata/spk2gender"

  ls $DATA/$s/ | sed -n /.*wav$/p |\
  while read wav ; do
    ((i++)) || true # bash specific
    if [[ $i -ge $every_n ]] ; then
      i=0
      pwav=$DATA/$s/$wav
      trn=`cat $DATA/$s/$wav.trn`
      echo "$wav $wav" >> $locdata/$s/spk2utt
      echo "$wav $trn" >> $locdata/$s/trans.txt
      echo "$wav $wav" >> $locdata/$s/utt2spk
      echo "$wav $pwav" >> $locdata/$s/wav.scp
      # all male
      echo "$wav m" >> $locdata/$s/spk2gender  
    fi
  done # while read wav 

  for f in spk2gender spk2utt trans.txt utt2spk wav.scp ; do
    sort "$locdata/$s/$f" -k1 -u -o "$locdata/$s/$f"  # sort in place
  done

done # for in $test_sets train


echo "--- Distributing the file lists to train and ($test_sets x $LMs) directories ..."
mkdir -p $WORK/train
cp -f $locdata/train/wav.scp $WORK/train/wav.scp || exit 1;
cp -f $locdata/train/trans.txt $WORK/train/text || exit 1;
cp -f $locdata/train/spk2utt $WORK/train/spk2utt || exit 1;
cp -f $locdata/train/utt2spk $WORK/train/utt2spk || exit 1;
cp -f $locdata/train/spk2gender $WORK/train/spk2gender || exit 1;
# utils/filter_scp.pl $WORK/train/spk2utt $locdata/spk2gender \
#   > $WORK/train/spk2gender || exit 1;
utils/validate_data_dir.sh --no-feats $WORK/train || exit 1;
echo DEBUG

for s in $test_sets ; do 
  for lm in $LMs; do
    tgt_dir=$WORK/${s}_`basename ${lm}`
    mkdir -p $tgt_dir
    cp -f $locdata/${s}/wav.scp $tgt_dir/wav.scp || exit 1;
    cp -f $locdata/${s}/trans.txt $tgt_dir/text || exit 1;
    cp -f $locdata/${s}/spk2utt $tgt_dir/spk2utt || exit 1;
    cp -f $locdata/${s}/utt2spk $tgt_dir/utt2spk || exit 1;
    # utils/filter_scp.pl $tgt_dir/spk2utt $locdata/spk2gender \
    #   > $tgt_dir/spk2gender || exit 1;  # fails here
    cp -f $locdata/${s}/spk2gender $tgt_dir/spk2gender || exit 1
    utils/validate_data_dir.sh --no-feats $tgt_dir || exit 1;
  done
done
