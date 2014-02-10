#!/bin/bash

export KALDI_ROOT=/ha/projects/vystadial/lib/pykaldi-kronos-build

source path.sh

tmpdir=hclg_tmp_data
localdir=$tmpdir/local # temporary directory
langdir=$tmpdir/lang  # temporary directory for lexicon related files
outputdir=models_tri2b_bmmi
oov='_SIL_'  # OOV words will be mapped to $oov 
am_dir='../../../tools/kaldi/model_voip_cs/exp/tri2b_mmi_b0.05'
AM=$am_dir/4.mdl   # acoustic model
tree=$am_dir/tree  # decision phonetic tree
lm_dir=../lm/
dict=$lm_dir/final.dict  # phonetic dictionary
vocab=$lm_dir/final.vocab
LM=$lm_dir/final.pg.arpa  # LM in arpa format

# TODO ask before deleting
rm -rf $tmpdir

pushd $am_dir
python download_models.py
popd
pushd $lm_dir
python download_models.py
popd

./build_hclg.sh $AM $tree $dict $vocab $LM $localdir $langdir $outputdir $oov
