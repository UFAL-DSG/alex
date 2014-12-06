#!/bin/bash
# Copyright Ondrej Platek Apache 2.0
set -e
renice 20 $$

# Load training parameters
. ./env_voip_cs.sh
# Source optional config if exists
[ -f env_voip_cs_CUSTOM.sh ] && . ./env_voip_cs_CUSTOM.sh

echo ; echo debug $KALDI_ROOT; echo
. ./path.sh

# If you have cluster of machines running GridEngine you may want to
# change the train and decode commands in the file below
. ./cmd.sh



./local/run_nnet_online.sh --gauss $gauss --pdf $pdf \
    --tgtdir $EXP/nnet2_online \
    $WORK $EXP "$LM_names" "$TEST_SETS" || exit 1 

./local/run_nnet_online-discriminative.sh --gauss $gauss --pdf $pdf \
    --nj $nj --srcdir $EXP/nnet2_online \
    $WORK $EXP "$LM_names" "$TEST_SETS" || exit 1 
