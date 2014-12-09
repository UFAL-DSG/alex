#!/bin/bash

# This is p-norm neural net training, with the "fast" script, on top of adapted
# 40-dimensional features.
set -e
# set -x

. ./cmd.sh
. ./path.sh


train_stage=-10
use_gpu=true
test_sets=
nj=8
num_jobs_nnet=4
gauss=19200
pdf=9000
srcdir=exp/nnet2_online
tgtdir=exp/nnet2_online_disc

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


# the make_denlats job is always done on CPU not GPU, since in any case
# the graph search and lattice determinization takes quite a bit of CPU.
# note: it's the sub-split option that determinies how many jobs actually
# run at one time.
local/check.sh steps/nnet2/make_denlats.sh --cmd "$decode_cmd -l mem_free=1G,ram_free=1G" \
    --nj $nj --sub-split 40 --num-threads 1 --parallel-opts "-pe smp 1" \
    --online-ivector-dir $EXP/nnet2_online/ivectors_train \
    $WORK/train $WORK/lang $srcdir ${srcdir}_denlats

if $use_gpu; then gpu_opt=yes; else gpu_opt=no; fi
local/check.sh steps/nnet2/align.sh  --cmd "$decode_cmd $gpu_opts" \
    --online-ivector-dir $EXP/nnet2_online/ivectors_train \
    --use-gpu $gpu_opt \
    --nj $nj $WORK/train $WORK/lang ${srcdir} ${srcdir}_ali

if $use_gpu; then
  local/check.sh steps/nnet2/train_discriminative.sh --cmd "$decode_cmd" --learning-rate 0.00002 \
    --online-ivector-dir $EXP/nnet2_online/ivectors_train \
    --num-jobs-nnet $num_jobs_nnet  --num-threads $num_threads --parallel-opts "$gpu_opts" \
      $WORK/train $WORK/lang \
    ${srcdir}_ali ${srcdir}_denlats ${srcdir}/final.mdl ${srcdir}_smbr
fi

# we'll do the decoding as 'online' decoding by using the existing
# _online directory but with extra models copied to it.
for epoch in 1 2 3 4; do
  cp ${srcdir}_smbr/epoch${epoch}.mdl ${srcdir}_online/smbr_epoch${epoch}.mdl
done


for epoch in 1 2 3 4; do
  # do the actual online decoding with iVectors, carrying info forward from 
  # previous utterances of the same speaker.
  # We just do the bd_tgpr decodes; otherwise the number of combinations 
  # starts to get very large.
  for lm in $LM_names ; do
    graph_dir=$EXP/tri3b/graph_${lm}
    for s in $TEST_SETS ; do
      tgt_dir=${s}_${lm}
      local/check.sh steps/online/nnet2/decode.sh --cmd "$decode_cmd" --nj $nj --iter smbr_epoch${epoch} \
        "$graph_dir" $WORK/${tgt_dir} ${srcdir}_online/decode_${tgt_dir}_${epoch} || exit 1;
    done
  done
done

if $use_gpu; then
  local/check.sh steps/nnet2/train_discriminative.sh --cmd "$decode_cmd" --learning-rate 0.00002 \
    --use-preconditioning true \
    --online-ivector-dir $EXP/nnet2_online/ivectors_train \
    --num-jobs-nnet $num_jobs_nnet  --num-threads $num_threads --parallel-opts "$gpu_opts" \
      $WORK/train $WORK/lang \
    ${srcdir}_ali ${srcdir}_denlats ${srcdir}/final.mdl ${srcdir}_smbr_precon
fi



for epoch in 1 2 3 4; do
  # we'll do the decoding as 'online' decoding by using the existing
  # _online directory but with extra models copied to it.
  cp ${srcdir}_smbr_precon/epoch${epoch}.mdl ${srcdir}_online/smbr_precon_epoch${epoch}.mdl

  # do the actual online decoding with iVectors, carrying info forward from 
  # previous utterances of the same speaker.
  # We just do the bd_tgpr decodes; otherwise the number of combinations 
  # starts to get very large.
  for lm in $LM_names ; do
    graph_dir=$EXP/tri3b/graph_${lm}
    for s in $TEST_SETS ; do
      tgt_dir=${s}_${lm}
      local/check.sh steps/online/nnet2/decode.sh --cmd "$decode_cmd" --nj $nj --iter smbr_precon_epoch${epoch} \
        "$graph_dir" $WORK/${tgt_dir} ${srcdir}_online/decode_precon_${tgt_dir}_${epoch} || exit 1;
    done
  done
done
