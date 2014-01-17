#!/bin/bash

TEST_SETS="dev test" 

# Directories set up
KALDI_ROOT=/ha/work/people/oplatek/kaldi
DATA_ROOT=/ha/projects/vystadial/data/asr/${data_lang}/voip  # expects subdirectories train + $TEST_SETS
WORK=`PWD`/model_voip_${DATA_LANG}
EXP=`PWD`/model_voip_${DATA_LANG}/exp

# Specify paths to arpa models. Paths may not contain spaces.
# Specify build0 or build1 or build2, .. for building (zero|uni|bi) -gram LM.
LMs="$DATA_ROOT/arpa_bigram build0"
# Settings for LM model weight tuned on development set and applied on test set.
MIN_LMW=4 
MAX_LMW=15

# Unset or empty DICTIONARY -> DICTIONARY is built from data
# export DICTIONARY="../../resources/lm/caminfo/dict"
unset DICTIONARY



# EveryN utterance is used for training
# everyN=3    ->   we use one third of data
EVERY_N=1

# Number of states for phonem training
pdf=1200

# Maximum number of Gaussians used for training
gauss=19200

# Cepstral Mean Normalisation: true/false
cmn=false

train_mmi_boost=0.05
