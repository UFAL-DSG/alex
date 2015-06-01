#!/bin/bash
# Copyright Ondrej Platek Apache 2.0
set -e
renice 20 $$

# Load training parameters
. ./env_voip_en.sh
# Source optional config if exists
[ -f env_voip_en_CUSTOM.sh ] && . ./env_voip_en_CUSTOM.sh

local/check_path.sh

. ./path.sh

# If you have cluster of machines running GridEngine you may want to
# change the train and decode commands in the file below
. ./cmd.sh

mkdir -p $WORK  $EXP
#######################################################################
#       Preparing acoustic features, LMs and helper files             #
#######################################################################

local/check.sh local/data_split.sh --every_n $EVERY_N \
    $DATA_ROOT $WORK/local "$LM_names" "$TEST_SETS" || exit 1

local/check.sh local/create_LMs.sh \
    --train_text $WORK/local/train/trans.txt \
    --arpa-paths "$LM_paths" --lm-names "$LM_names" \
    $WORK/local/lm || exit 1

local/check.sh local/prepare_en_transcription.sh $WORK/local/lm $WORK/local/dict || exit 1

local/train_base.sh
