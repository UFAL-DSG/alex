#!/bin/bash

export KALDI_ROOT=/ha/work/people/oplatek/kaldi
tmpdir=data
localdir=$tmpdir/local # temporary directory
langdir=$tmpdir/lang  # temporary directory for lexicon related files
outputdir=models
oov='_SIL_'  # OOV words will be mapped to $oov 
AM=final.mdl   # acoustic model
tree=tree  # decision phonetic tree
dict=../lm/final.dict  # phonetic dictionary
vocab=../lm/final.vocab
LM=../lm/final.bg.arpa  # LM in arpa format

# TODO ask before deleting
rm -rf $tmpdir
rm -rf $outputdir

./build_hclg.sh $AM $tree $dict $vocab $LM $localdir $langdir $outputdir $oov
