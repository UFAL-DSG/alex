#!/bin/bash

# This is p-norm neural net training, with the "fast" script, on top of adapted
# 40-dimensional features.
set -e
set -x

echo -e "\nTODO Debug this script which is based on egs/wsj/s5/local/online/run_nnet2_baseline.sh baseline online DNN decoding without ivectors\n"
echo -e "\nTODO extend this script with ivectors based on egs/wsj/s5/local/online/run_nnet2.sh\n"

. ./cmd.sh
. ./path.sh

# Load training parameters
. ./env_voip_cs.sh
# Source optional config if exists
[ -f env_voip_cs_CUSTOM.sh ] && . ./env_voip_cs_CUSTOM.sh

train_stage=-10
use_gpu=true
test_sets=
nj=6
num_jobs_nnet=4


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
  dir=$EXP/nnet5a_clean_100_gpu
else
  # with just 4 jobs this might be a little slow.
  num_threads=16
  parallel_opts="-pe smp $num_threads" 
  minibatch_size=128
  dir=$EXP/nnet
fi

. utils/parse_options.sh


# Train tri3b, which is LDA+MLLT+SAT
utils/check.sh steps/train_sat.sh --cmd "$train_cmd" \
  $pdf $gauss $WORK/train $WORK/lang $EXP/tri2b_ali $EXP/tri3b || exit 1;

utils/check.sh steps/align_fmllr.sh --nj $nj --cmd "$train_cmd" \
  $WORK/train $WORK/lang $EXP/tri3b $EXP/tri3b_ali || exit 1;

utils/check.sh steps/nnet2/train_pnorm_fast.sh --stage $train_stage \
 --samples-per-iter 400000 \
 --parallel-opts "$parallel_opts" \
 --num-threads "$num_threads" \
 --minibatch-size "$minibatch_size" \
 --num-jobs-nnet $num_jobs_nnet  --mix-up 8000 \
 --initial-learning-rate 0.01 --final-learning-rate 0.001 \
 --num-hidden-layers 4 \
 --pnorm-input-dim 2000 --pnorm-output-dim 400 \
 --cmd "$decode_cmd" \
  $WORK/train $WORK/lang $EXP/tri3b_ali $dir || exit 1

for lm in $LM_names ; do
  lm=`basename "$lm"`
  graph_dir=$EXP/tri3b/graph_${lm}
  for s in $TEST_SETS ; do
    tgt_dir=${s}_${lm}
    utils/check.sh steps/nnet2/decode.sh --nj $nj --cmd "$decode_cmd" \
      $EXP/tri3b/graph_${lm} $WORK/$tgt_dir $dir/decode_${tgt_dir} || exit 1
  done
done

steps/online/nnet2/prepare_online_decoding.sh $WORK/lang "$dir" ${dir}_online || exit 1

for lm in $LM_names ; do
  lm=`basename "$lm"`
  graph_dir=$EXP/tri3b/graph_${lm}
  for s in $TEST_SETS ; do
    tgt_dir=${s}_${lm}
    # Decode. the --per-utt true option makes no difference to the results here
    utils/check.sh steps/online/nnet2/decode.sh --nj $nj --cmd "$decode_cmd" \
      --per-utt true \
      $EXP/tri3b/graph_${lm} $WORK/$tgt_dir $dir/decode_${tgt_dir} || exit 1
  done
done

exit 0;

