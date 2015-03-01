#!/bin/bash

# This is a basic online neural net training.
# After this you can do discriminative training with run_nnet2_discriminative.sh.
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
srcdir=$EXP/tri2b
tgtdir=$EXP/nnet2

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

# To train a diagonal UBM we don't need very much data, but we still use full one
# the $srcdir (tri2b) is the input dir; the choice of this is not critical as we just use
# it for the LDA matrix.  Since the iVectors don't make a great deal of difference,
# we'll use 256 Gaussians for speed.
local/check.sh  steps/online/nnet2/train_diag_ubm.sh --cmd "$train_cmd" --nj $nj --parallel-opts '-pe smp 1' --num-threads 1 --num-frames 200000 \
    $WORK/train 256 $srcdir $tgtdir/diag_ubm

# even though $nj is just 10, each job uses multiple processes and threads.
local/check.sh steps/online/nnet2/train_ivector_extractor.sh --cmd "$train_cmd" --nj $nj --num-processes 1 --num-threads 1 \
    $WORK/train $tgtdir/diag_ubm $tgtdir/extractor || exit 1;

# We extract iVectors on all the $WORK/train data, which will be what we
# train the system on.
# having a larger number of speakers is helpful for generalization, and to
# handle per-utterance decoding well (iVector starts at zero).
local/check.sh steps/online/nnet2/copy_data_dir.sh --utts-per-spk-max 2 $WORK/train $WORK/train_max2

local/check.sh steps/online/nnet2/extract_ivectors_online.sh \
    --cmd "$train_cmd" --nj $nj \
    $WORK/train_max2 $tgtdir/extractor $tgtdir/ivectors_train || exit 1;

# Because we have a lot of data here and we don't want the training to take
# too long so we reduce the number of epochs from the defaults (15 + 5) to (8
# + 4).
# The number of parameters is a bit smaller than the baseline system we had in mind
# (../nnet2/run_5d.sh), which had pnorm input/output dim 2000/400 and 4 hidden
# layers, versus our 2400/300 and 4 hidden layers, even though we're training
# on more data than the baseline system (we're changing the proportions of
# input/output dim to be closer to 10:1 which is what we believe works well).
# The motivation of having fewer parameters is that we want to demonstrate the
# capability of doing real-time decoding, and if the network was too bug we
# wouldn't be able to decode in real-time using a CPU.
#
# I copied the learning rates from wsj/s5/local/nnet2/run_5d.sh
local/check.sh steps/nnet2/train_pnorm_simple2.sh --stage $train_stage \
    --num-epochs 12 \
    --splice-width 7 --feat-type raw \
    --online-ivector-dir $tgtdir/ivectors_train \
    --cmvn-opts "--norm-means=false --norm-vars=false" \
    --num-threads "$num_threads" \
    --minibatch-size "$minibatch_size" \
    --parallel-opts "$parallel_opts" \
    --num-jobs-nnet $num_jobs_nnet \
    --num-hidden-layers 4 \
    --mix-up 4000 \
    --initial-learning-rate 0.02 --final-learning-rate 0.004 \
    --cmd "$gpu_cmd" \
    --pnorm-input-dim 2400 \
    --pnorm-output-dim 300 \
    --combine-num-threads 1 \
    --combine-parallel-opts "$parallel_opts" \
    $WORK/train $WORK/lang ${srcdir}_ali $tgtdir || exit 1;

for s in $TEST_SETS ; do
    local/check.sh steps/online/nnet2/extract_ivectors_online.sh \
        --cmd "$train_cmd" --nj $nj \
        $WORK/local/${s} $tgtdir/extractor $tgtdir/ivectors_${s} || exit 1;
done

local/check.sh steps/online/nnet2/prepare_online_decoding.sh $WORK/lang \
    $tgtdir/extractor $tgtdir ${tgtdir}_online || exit 1

exit 0
