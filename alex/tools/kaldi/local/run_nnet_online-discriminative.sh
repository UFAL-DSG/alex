#!/bin/bash

# This is a dicsriminative neural net trainign.
set -e
#set -x

. ./cmd.sh
. ./path.sh


train_stage=-10
use_gpu=true
test_sets=
nj=8
num_jobs_nnet=4
gauss=19200
pdf=9000
graphdir=$EXP/tri2b \
srcdir=$EXP/nnet2
tgtdir=$EXP/nnet2_smbr

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
else
  num_threads=4
  parallel_opts="-pe smp $num_threads" 
  minibatch_size=128
fi

nj=`cat $srcdir/num_jobs` || exit 1;

mkdir -p $tgtdir

# the make_denlats job is always done on CPU not GPU, since in any case
# the graph search and lattice determinization takes quite a bit of CPU.
# note: it's the sub-split option that determinies how many jobs actually
# run at one time.
local/check.sh steps/nnet2/make_denlats.sh --cmd "$gpu_cmd" \
    --nj $gpu_nj --sub-split 40 --num-threads 1 --parallel-opts "-pe smp 1" \
    --online-ivector-dir $srcdir/ivectors_train \
    $WORK/train $WORK/lang $srcdir ${srcdir}_denlats

if $use_gpu; then gpu_opt=yes; else gpu_opt=no; fi
local/check.sh steps/nnet2/align.sh  --cmd "$gpu_cmd" \
    --online-ivector-dir $srcdir/ivectors_train \
    --use-gpu $gpu_opt \
    --nj $gpu_nj $WORK/train $WORK/lang ${srcdir} ${srcdir}_ali

if $use_gpu; then
  local/check.sh steps/nnet2/train_discriminative.sh --cmd "$gpu_cmd" --learning-rate 0.00002 \
    --online-ivector-dir $srcdir/ivectors_train \
    --num-jobs-nnet $num_jobs_nnet  --num-threads $num_threads --parallel-opts "$parallel_opts" \
      $WORK/train $WORK/lang \
    ${srcdir}_ali ${srcdir}_denlats ${srcdir}/final.mdl ${tgtdir}
fi


for epoch in 1 2 3 4; do
  # do the actual online decoding with iVectors, carrying info forward from
  # previous utterances of the same speaker.
  # We just do the bd_tgpr decodes; otherwise the number of combinations
  # starts to get very large.
  for lm in $LM_names ; do
    local/check.sh utils/mkgraph.sh $WORK/lang_${lm} $tgtdir $tgtdir/graph_${lm} || exit 1
    for s in $TEST_SETS ; do
      tgt_dir=${s}_${lm}
      local/check.sh steps/nnet2/decode.sh --cmd "$gpu_cmd" --nj $gpu_nj --iter epoch${epoch} \
        --online-ivector-dir $srcdir/ivectors_${s} \
        $tgtdir/graph_${lm} $WORK/${tgt_dir} ${tgtdir}/decode_${tgt_dir}_${epoch} || exit 1;
    done
  done
done

local/check.sh steps/online/nnet2/prepare_online_decoding.sh $WORK/lang \
  $srcdir/extractor $tgtdir ${tgtdir}_online || exit 1

# we'll do the decoding as 'online' decoding by using the existing
# _online directory but with extra models copied to it.
for epoch in 1 2 3 4; do
  cp ${tgtdir}/epoch${epoch}.mdl ${tgtdir}_online/smbr_epoch${epoch}.mdl
done


for epoch in 1 2 3 4; do
  # do the actual online decoding with iVectors, carrying info forward from 
  # previous utterances of the same speaker.
  # We just do the bd_tgpr decodes; otherwise the number of combinations 
  # starts to get very large.
  for lm in $LM_names ; do
    for s in $TEST_SETS ; do
      tgt_dir=${s}_${lm}
      local/check.sh steps/online/nnet2/decode.sh --cmd "$gpu_cmd" --nj $gpu_nj --iter smbr_epoch${epoch} \
        $tgtdir/graph_${lm} $WORK/${tgt_dir} ${tgtdir}_online/decode_${tgt_dir}_${epoch} || exit 1;
    done
  done
done

exit 0
