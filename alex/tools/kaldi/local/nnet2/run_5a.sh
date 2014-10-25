#!/bin/bash

# This is p-norm neural net training, with the "fast" script, on top of adapted
# 40-dimensional features.


train_stage=-10
use_gpu=true
test_sets=

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
  dir=exp/nnet5a_clean_100_gpu
else
  # with just 4 jobs this might be a little slow.
  num_threads=16
  parallel_opts="-pe smp $num_threads" 
  minibatch_size=128
  dir=exp/nnet5a_clean_100
fi

. ./cmd.sh
. ./path.sh
. utils/parse_options.sh


# Train tri3b, which is LDA+MLLT+SAT
steps/train_sat.sh --cmd "$train_cmd" \
  2500 15000 data/train_10k data/lang exp/tri2b_ali exp/tri3b || exit 1;

steps/align_fmllr.sh --nj 20 --cmd "$train_cmd" \
  data/train data/lang exp/tri3b exp/tri3b_ali || exit 1;

steps/nnet2/train_pnorm_fast.sh --stage $train_stage \
 --samples-per-iter 400000 \
 --parallel-opts "$parallel_opts" \
 --num-threads "$num_threads" \
 --minibatch-size "$minibatch_size" \
 --num-jobs-nnet 4  --mix-up 8000 \
 --initial-learning-rate 0.01 --final-learning-rate 0.001 \
 --num-hidden-layers 4 \
 --pnorm-input-dim 2000 --pnorm-output-dim 400 \
 --cmd "$decode_cmd" \
  data/train data/lang exp/tri3b_ali $dir || exit 1


for test in dev_clean dev_other; do
  steps/nnet2/decode.sh --nj 20 --cmd "$decode_cmd" \
    --transform-dir exp/tri3b/decode_tgsmall_$test \
    exp/tri3b/graph_tgsmall data/$test $dir/decode_tgsmall_$test || exit 1;
  steps/lmrescore.sh --cmd "$decode_cmd" data/lang_test_{tgsmall,tgmed} \
    data/$test $dir/decode_{tgsmall,tgmed}_$test  || exit 1;
done

exit 0;

