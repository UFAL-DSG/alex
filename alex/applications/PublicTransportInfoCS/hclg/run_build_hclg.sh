#!/bin/bash

export KALDI_ROOT=/ha/work/people/oplatek/kaldi

source path.sh

tmpdir=hclg_tmp_data
localdir=$tmpdir/local # temporary directory
langdir=$tmpdir/lang  # temporary directory for lexicon related files
outputdir=models
oov='_SIL_'  # OOV words will be mapped to $oov 
mdl_dir=../../../resources/asr/voip_cs/kaldi
AM=$mdl_dir/tri2b_bmmi.mdl   # acoustic model
tree=$mdl_dir/tri2b_bmmi.tree  # decision phonetic tree
lm_dir=../lm/
dict=$lm_dir/final.dict  # phonetic dictionary
vocab=$lm_dir/final.vocab
LM=$lm_dir/final.tg.arpa  # LM in arpa format

# TODO ask before deleting
rm -rf $tmpdir

pushd $mdl_dir
python download_models.py
popd
pushd $lm_dir
python download_models.py
popd

./build_hclg.sh $AM $tree $dict $vocab $LM $localdir $langdir $outputdir $oov
