#!/bin/bash

# Trains up word internal models for English.

. env_voip_en.sh

date

echo "Training word internal triphone model for English"
echo ""
echo "Environment variables:"
echo "TRAIN_COMMON       = $TRAIN_COMMON"
echo "TRAIN_SCRIPTS      = $TRAIN_SCRIPTS"
echo "HEREST_SPLIT       = $HEREST_SPLIT"
echo "HEREST_THREADS     = $HEREST_THREADS"
echo ""
echo "TRAIN_DATA_SOURCE  = $TRAIN_DATA_SOURCE"
echo "TEST_DATA_SOURCE   = $TEST_DATA_SOURCE"
echo ""
echo "WORK_DIR           = $WORK_DIR"
echo "TEMP_DIR           = $TEMP_DIR"
echo "LOG_DIR            = $LOG_DIR"
echo "TRAIN_DATA         = $TRAIN_DATA"
echo "TEST_DATA          = $TEST_DATA"
echo ""

cd $WORK_DIR

# We need to massage the CMU dictionary for our use
echo "Preparing CMU English dictionary ..."
$TRAIN_SCRIPTS/prep_cmu_dict.sh

# Code the audio files to MFCC feature vectors
echo "Coding test audio ..."
$TRAIN_SCRIPTS/prep_param_test.sh

echo "Coding train audio ..."
$TRAIN_SCRIPTS/prep_param_train.sh

# Intial setup of language model, dictionary, training and test MLFs
echo "Building unigram language models and dictionary..."
$TRAIN_SCRIPTS/build_lm.sh
echo "Building training MLF ..."
$TRAIN_SCRIPTS/make_mlf_train.sh 
echo "Building test MLF ..."
$TRAIN_SCRIPTS/make_mlf_test.sh

date 

# Get the basic monophone models trained
echo "Flat starting monophones ..."
$TRAIN_SCRIPTS/flat_start.sh

# Create a new MLF that is aligned based on our monophone model
echo "Aligning with monophones ..."
$TRAIN_SCRIPTS/align_mlf.sh

# More training for the monophones, create triphones, train
# triphones, tie the triphones, train tied triphones, then
# mixup the number of Gaussians per state.
echo "Training monophones ..."
$TRAIN_SCRIPTS/train_mono.sh
echo "Prepping triphones ..."
$TRAIN_SCRIPTS/prep_tri.sh
echo "Training triphones ..."
$TRAIN_SCRIPTS/train_tri.sh

# These values of RO and TB seem to work fairly well, but
# there may be more optimal values.
echo "Prepping state-tied triphones ..."
$TRAIN_SCRIPTS/prep_tied.sh 200 750

echo "Training state-tied triphones ..."
$TRAIN_SCRIPTS/train_tied.sh
echo "Mixing up ..."
$TRAIN_SCRIPTS/train_mixup.sh

date 

# Evaluate how we did on zerogram language model
echo "Decoding zerogram language model"
$TRAIN_SCRIPTS/eval_test_no_lat.sh hmm42 _ro200_tb750_prune350_zerogram 350.0 -0.0 22.0 $WORK_DIR/wdnet_zerogram

date 

# Evaluate how we did on bigram language model if it is available
if [ -d $WORK_DIR/wdnet_bigram ]
then
  echo "Decoding bigram language model"
  $TRAIN_SCRIPTS/eval_test_no_lat.sh hmm42 _ro200_tb750_prune350_bigram 350.0 -0.0 15.0 $WORK_DIR/wdnet_bigram
fi

# Re-align the training data with the best triphone models
echo "Aligning with triphones ..."
$TRAIN_SCRIPTS/realign.sh hmm42 tiedlist

echo "End of training"

date
