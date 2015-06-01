#!/bin/bash

# This is a dicsriminative [SMBR] neural net training.
set -e
#set -x

. ./cmd.sh
. ./path.sh


train_stage=-10
use_gpu=true
test_sets=
nj=8
num_jobs_nnet=3
gauss=19200
pdf=9000
srcdir=$EXP/nnet2
tgtdir=$EXP/nnet2_smbr

. utils/parse_options.sh

if [ $# -ne 2 ] ; then
    echo usage $0: WORK EXP
    exit 1
fi
WORK=$1
EXP=$2

if $use_gpu; then
    if ! cuda-compiled; then
        cat <<EOF && exit 1
This script is intended to be used with GPUs but you have not compiled Kaldi with CUDA 
If you want to use GPUs (and have them), go to src/, and configure and make on a machine
where "nvcc" is installed.
EOF
    fi
    parallel_opts="-l gpu=1"
    num_threads=1
    minibatch_size=512
else
    num_threads=4
    parallel_opts="-pe smp $num_threads"
    minibatch_size=128
fi

nj=`cat $srcdir/num_jobs` || exit 1;

mkdir -p $tgtdir

local/check.sh steps/nnet2/make_denlats.sh --nj "$nj" --cmd "$train_cmd" \
    --sub-split 40 --num-threads 1 --parallel-opts "-pe smp 1" \
    --online-ivector-dir $srcdir/ivectors_train \
    --beam $smbr_beam --lattice-beam $smbr_lat_beam \
    $WORK/train $WORK/lang $srcdir ${srcdir}_denlats

local/check.sh steps/nnet2/align.sh --nj "$nj" --cmd "$train_cmd" \
    --online-ivector-dir $srcdir/ivectors_train \
    $WORK/train $WORK/lang $srcdir ${srcdir}_ali

# SMBR dicriminative training
local/check.sh steps/nnet2/train_discriminative.sh --cmd "$gpu_cmd" --learning-rate 0.00002 \
    --online-ivector-dir $srcdir/ivectors_train \
    --num-jobs-nnet $num_jobs_nnet  --num-threads $num_threads --parallel-opts "$parallel_opts" \
    $WORK/train $WORK/lang \
    ${srcdir}_ali ${srcdir}_denlats ${srcdir}/final.mdl ${tgtdir}

local/check.sh steps/online/nnet2/prepare_online_decoding.sh $WORK/lang \
  $srcdir/extractor $tgtdir ${tgtdir}_online || exit 1

exit 0
