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
echo "Using a medium AM"
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-16--17-44-34-s4k-g100k/tri2b_bmmi.mdl
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-16--17-44-34-s4k-g100k/tri2b_bmmi.tree
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-16--17-44-34-s4k-g100k/tri2b_bmmi.mat
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-16--17-44-34-s4k-g100k/mfcc.conf
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-16--17-44-34-s4k-g100k/silence.csl
wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-16--17-44-34-s4k-g100k/phones.txt

#echo "Using a large AM - does not work that well"
#wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-23--05-40-30-s8k-g200k/tri2b_bmmi.mdl
#wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-23--05-40-30-s8k-g200k/tri2b_bmmi.tree
#wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-23--05-40-30-s8k-g200k/tri2b_bmmi.mat
#wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-23--05-40-30-s8k-g200k/mfcc.conf
#wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-23--05-40-30-s8k-g200k/silence.csl
#wget --timestamping  https://vystadial.ms.mff.cuni.cz/download/kams/en_super_no_dnn-2015-04-23--05-40-30-s8k-g200k/phones.txt
popd

pushd $lm_dir
python download_models.py
popd

../../../corpustools/kaldi_build_hclg.sh $AM $tree $mfcc $mat $sil $dict $vocab $LM $localdir $langdir $outputdir $oov
