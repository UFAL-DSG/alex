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
#   d) $TYPE.spk2utt
#   e) $TYPE.spk2gender  all speakers are male
# we have ID-recording = ID-speaker

# The vystadial data are specific by having following marks in transcriptions
# _INHALE_
# _LAUGH_ 
# _EHM_HMM_ 
# _NOISE_
# _EHM_HMM_
# _SIL_

# renice 20 $$

every_n=1
[ -f path.sh ] && . ./path.sh # source the path.
. utils/parse_options.sh || exit 1;


msg="Usage: $0 [--every-n 30] <data-directory>";
if [ $# -gt 1 ] ; then
    echo "$msg"; exit 1;
fi
if [ $# -eq 0 ] ; then
    echo "$msg"; exit 1;
fi

DATA=$1

echo "=== Starting initial Vystadial data preparation ..."
echo "--- Making test/train data split from $DATA taking every $every_n recording..."

locdata=data/local
loctmp=$locdata/tmp
rm -rf $loctmp >/dev/null 2>&1
mkdir -p $locdata
mkdir -p $loctmp

i=0
for d in $test_sets train ; do
    ls $DATA/$d/ | sed -n /.*wav$/p |\
    while read wav ; do
        ((i++)) # bash specific
        if [[ $i -ge $every_n ]] ; then
            i=0
            pwav=$DATA/$d/$wav
            trn=`cat $DATA/$d/$wav.trn`
            echo "$wav $pwav" >> ${loctmp}/${d}_wav.scp.unsorted
            echo "$wav $wav" >> ${loctmp}/${d}.utt2spk.unsorted
            echo "$wav $wav" >> ${loctmp}/${d}.spk2utt.unsorted
            echo "$wav $trn" >> ${loctmp}/${d}_trans.txt.unsorted
            echo "$wav M" >> ${loctmp}/spk2gender.unsorted
        fi
    done # while read wav 

    # Sorting
    for unsorted in _wav.scp.unsorted _trans.txt.unsorted \
        .spk2utt.unsorted .utt2spk.unsorted _wav.scp.unsorted
    do
       u="${d}${unsorted}"
       s=`echo "$u" | sed -e s:.unsorted::`
       sort "${loctmp}/$u" -k1 > "${locdata}/$s"
    done # for unsorted

    mkdir -p data/$d
    cp $locdata/${d}_wav.scp data/$d/wav.scp || exit 1;
    cp $locdata/${d}_trans.txt data/$d/text || exit 1;
    cp $locdata/$d.spk2utt data/$d/spk2utt || exit 1;
    cp $locdata/$d.utt2spk data/$d/utt2spk || exit 1;
    if [[ ! -z "$TEST_ZERO_GRAMS" ]] ; then
        mkdir -p data/${d}0
        for f in wav.scp text spk2utt utt2spk ; do
            cp data/$d/$f data/${d}0
        done
    fi

done # for in $test_sets train

# set 1:1 relation for spk2utt: spk in $test_sets AND train
sort "${loctmp}/spk2gender.unsorted" -k1 > "${locdata}/spk2gender" 
utils/filter_scp.pl data/$d/spk2utt $locdata/spk2gender > data/$d/spk2gender || exit 1;
