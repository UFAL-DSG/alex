#!/bin/bash

#export KALDI_ROOT=/ha/projects/vystadial/lib/kronos/pykaldi
export KALDI_ROOT=/a/kronosh/oplatek/kaldi-kronos
#export KALDI_ROOT=/app/pykaldi/kaldi

source path.sh

tmpdir=hclg_tmp_data
localdir=$tmpdir/local # temporary directory
langdir=$tmpdir/lang  # temporary directory for lexicon related files
outputdir=models
oov='_SIL_'  # OOV words will be mapped to $oov 
am_dir=$tmpdir/model
AM=$am_dir/tri2b_bmmi.mdl   # acoustic model
tree=$am_dir/tri2b_bmmi.tree  # decision phonetic tree
lm_dir=../lm/
dict=$lm_dir/final.dict  # phonetic dictionary
vocab=$lm_dir/final.vocab
LM=$lm_dir/final.pg.arpa  # LM in arpa format

mat=$am_dir/tri2b_bmmi.mat
mfcc=$am_dir/mfcc.conf
sil=$am_dir/silence.csl

rm -rf $tmpdir

mkdir -p $am_dir
pushd $am_dir
MODEL_NAME='cs_voip-2015-09-09--22-53-05'
echo "Using model:" $MODEL_NAME
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/$MODEL_NAME/tri2b_bmmi.mdl
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/$MODEL_NAME/tri2b_bmmi.tree
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/$MODEL_NAME/tri2b_bmmi.mat
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/$MODEL_NAME/mfcc.conf
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/$MODEL_NAME/silence.csl
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/$MODEL_NAME/phones.txt

popd

pushd $lm_dir
python download_models.py
popd

../../../corpustools/kaldi_build_hclg.sh $AM $tree $mfcc $mat $sil $dict $vocab $LM $localdir $langdir $outputdir $oov
