#!/bin/bash

# This is our online neural net build.
# After this you can do discriminative training with run_nnet2_discriminative.sh.
set -e
# set -x

. ./cmd.sh
. ./path.sh


train_stage=-10
use_gpu=true
test_sets=
nj=8
num_jobs_nnet=8
gauss=19200
pdf=9000
tgtdir=$EXP/nnet2_online

. utils/parse_options.sh

if [ $# -ne 4 ] ; then
    echo usage $0: WORK EXP LM_names TEST_SETS
    exit 1
fi
WORK=$1
EXP=$2
LM_names="$3"
TEST_SETS="$4"

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
  dir=$tgtdir
else
  # with just 4 jobs this might be a little slow.
  num_threads=16
  parallel_opts="-pe smp $num_threads" 
  minibatch_size=128
  dir=${tgtdir}_NOGPU
fi

mkdir -p $EXP/nnet2_online

# To train a diagonal UBM we don't need TODO very much data, but we still use full one
# the tri2b is the input dir; the choice of this is not critical as we just use
# it for the LDA matrix.  Since the iVectors don't make a great deal of difference,
# we'll use 256 Gaussians for speed.
local/check.sh  steps/online/nnet2/train_diag_ubm.sh --cmd "$train_cmd" --nj 10 --num-frames 200000 \
    $WORK/train 256 $EXP/tri2b $EXP/nnet2_online/diag_ubm

# even though $nj is just 10, each job uses multiple processes and threads.
local/check.sh steps/online/nnet2/train_ivector_extractor.sh --cmd "$train_cmd" --nj 1 \
$WORK/train $EXP/nnet2_online/diag_ubm $EXP/nnet2_online/extractor || exit 1;

# TODO probably useless but nice for debugging
# We extract iVectors on all the $WORK/train data, which will be what we
# train the system on.
# having a larger number of speakers is helpful for generalization, and to
# handle per-utterance decoding well (iVector starts at zero).
local/check.sh steps/online/nnet2/copy_data_dir.sh --utts-per-spk-max 2 $WORK/train $WORK/train_max2

local/check.sh steps/online/nnet2/extract_ivectors_online.sh \
    --cmd "$train_cmd" --nj 1 \
    $WORK/train_max2 $EXP/nnet2_online/extractor $EXP/nnet2_online/ivectors_train || exit 1;


# Because we have a lot of data here and we don't want the training to take
# too long so we reduce the number of epochs from the defaults (15 + 5) to (8
# + 4).

# Regarding the number of jobs, we decided to let others run their jobs too so
# we only use 6 GPUs) (we only have 10 GPUs on our queue at JHU).  The number
# of parameters is a bit smaller than the baseline system we had in mind
# (../nnet2/run_5d.sh), which had pnorm input/output dim 2000/400 and 4 hidden
# layers, versus our 2400/300 and 4 hidden layers, even though we're training
# on more data than the baseline system (we're changing the proportions of
# input/output dim to be closer to 10:1 which is what we believe works well).
# The motivation of having fewer parameters is that we want to demonstrate the
# capability of doing real-time decoding, and if the network was too bug we
# wouldn't be able to decode in real-time using a CPU.
#
# I copied the learning rates from wsj/s5/local/nnet2/run_5d.sh
local/check.sh steps/nnet2/train_pnorm_simple.sh --stage $train_stage \
  --num-epochs 12 \
  --splice-width 7 --feat-type raw \
  --online-ivector-dir $EXP/nnet2_online/ivectors_train \
  --cmvn-opts "--norm-means=false --norm-vars=false" \
  --num-threads "$num_threads" \
  --minibatch-size "$minibatch_size" \
  --parallel-opts "$parallel_opts" \
  --num-jobs-nnet $num_jobs_nnet \
  --num-hidden-layers 4 \
  --mix-up 4000 \
  --initial-learning-rate 0.02 --final-learning-rate 0.004 \
  --cmd "$decode_cmd" \
  --pnorm-input-dim 2400 \
  --pnorm-output-dim 300 \
  $WORK/train $WORK/lang $EXP/tri3b_ali $dir || exit 1;

for s in $TEST_SETS ; do
  local/check.sh steps/online/nnet2/extract_ivectors_online.sh \
    --cmd "$train_cmd" --nj 1 \
    $WORK/local/${s} $EXP/nnet2_online/extractor $EXP/nnet2_online/ivectors_${s} || exit 1;
done


for lm in $LM_names ; do
  graph_dir=$EXP/tri3b/graph_${lm}
  local/check.sh utils/mkgraph.sh $WORK/lang_${lm} $EXP/tri3b $EXP/tri3b/graph_${lm} || exit 1
  for s in $TEST_SETS ; do
    tgt_dir=${s}_${lm}
    local/check.sh steps/nnet2/decode.sh --nj $nj --cmd "$decode_cmd" \
      --online-ivector-dir $EXP/nnet2_online/ivectors_${s} \
      $EXP/tri3b/graph_${lm} $WORK/$tgt_dir $dir/decode_${tgt_dir} || exit 1
  done
done

local/check.sh steps/online/nnet2/prepare_online_decoding.sh $WORK/lang \
  $EXP/nnet2_online/extractor $dir ${dir}_online || exit 1

for lm in $LM_names ; do
  graph_dir=$EXP/tri3b/graph_${lm}
  for s in $TEST_SETS ; do
    tgt_dir=${s}_${lm}
    # Decode. the --per-utt true option makes no difference to the results here
    local/check.sh steps/online/nnet2/decode.sh --nj $nj --cmd "$decode_cmd" \
      $EXP/tri3b/graph_${lm} $WORK/$tgt_dir ${dir}_online/decode_${tgt_dir} || exit 1
  done
done

exit 0
