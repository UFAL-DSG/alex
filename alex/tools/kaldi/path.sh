#!/bin/bash
# Needed for "correct" sorting
export LC_ALL=C

if [ ! -d "$KALDI_ROOT" ] ; then
  echo "KALDI_ROOT need to be set to point to directory"
  exit 1
fi

# adding Kaldi binaries to path
export PATH=$KALDI_ROOT/src/bin:$KALDI_ROOT/tools/openfst/bin:$KALDI_ROOT/tools/irstlm/bin/:$KALDI_ROOT/src/fstbin/:$KALDI_ROOT/src/gmmbin/:$KALDI_ROOT/src/featbin/:$KALDI_ROOT/src/lm/:$KALDI_ROOT/src/sgmmbin/:$KALDI_ROOT/src/sgmm2bin/:$KALDI_ROOT/src/fgmmbin/:$KALDI_ROOT/src/kwsbin/:$KALDI_ROOT/src/latbin/:$KALDI_ROOT/src/nnet2bin/:$KALDI_ROOT/src/nnetbin/:$KALDI_ROOT/src/lmbin/:$KALDI_ROOT/src/ivectorbin:$KALDI_ROOT/src/online2bin:$KALDI_ROOT/src/onlinebin:$PWD:$PATH

export PATH=$PWD/utils:$PWD/steps:$PATH
export LD_LIBRARY_PATH=$KALDI_ROOT/tools/openfst/lib:$KALDI_ROOT/tools/openfst/lib/fst:$LD_LIBRARY_PATH

# Fix for loading cuda on all computers also without the GPU e.g. on CLUSTER
export LD_LIBRARY_PATH=/opt/lib/CUDA/cuda-6.5/lib64:/opt/lib/CUDA/cuda-6.5/lib:$LD_LIBRARY_PATH
