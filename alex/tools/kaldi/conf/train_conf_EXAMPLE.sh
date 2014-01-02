#!/bin/bash

# NEED TO BE SET
export KALDI_ROOT=/ha/work/people/oplatek/kaldi

data_lang=cs
export DATA_ROOT=/ha/projects/vystadial/data/asr/en/voip

export test_sets="dev test"

export LM_ORDER=2
# Unset or empty ARPA_MODEL variable means that the script will build the LM itself
export ARPA_MODEL="/ha/projects/vystadial/data/asr/cs/voip/arpa_bigram"
# unset ARPA_MODEL

# Should I create and use 0-gram LM for decoding from testing data?
export TEST_ZERO_GRAMS="yes"
# unset TEST_ZERO_GRAMS


# Unset or empty DICTIONARY -> DICTIONARY is built from data 
# export DICTIONARY="/ha/projects/vystadial/git/alex/resources/lm/caminfo/dict"
unset DICTIONARY

# Directory for saving MFCC. Possibly huge. 
export MFCC_DIR="./mfcc"

# Removing OOV from LM (yes|no=everything else from yes means no)
export NOOOV="yes"
# unset NOOOV


# EveryN utterance is used for training 
# everyN=3    ->   we use one third of data
everyN=1

# Number of utterances used for training monophone models:
# monoTrainData=150
unset monoTrainData  # use full data

# Number of states for phonem training
pdf=1200

# Maximum number of Gaussians used for training
gauss=41000

# Cepstral Mean Normalisation: true/false
cmn=false

train_mmi_boost=0.05
