#!/bin/bash
# These variable settings are used by the HTK training recipe for Czech.
#
# Using the bash shell, you can source it ( `. XXX` )
# from the training script.
#
# You'll obviously need to change the paths to
# reflect reality in your world.

HOME_DIR=`pwd`;export HOME_DIR

# Directories where the speech corpora live
DATA_SOURCE_DIR=$HOME_DIR/data_voip_cs;export DATA_SOURCE_DIR
TRAIN_DATA_SOURCE=$DATA_SOURCE_DIR/train;export TRAIN_DATA_SOURCE
TEST_DATA_SOURCE=$DATA_SOURCE_DIR/test;export TEST_DATA_SOURCE

# Work directory we use during training
WORK_DIR=$HOME_DIR/model_voip_cs;export WORK_DIR
TRAIN_DATA=$WORK_DIR/train;export TRAIN_DATA
TEST_DATA=$WORK_DIR/test;export TEST_DATA

TEMP_DIR=$WORK_DIR/temp;export TEMP_DIR
LOG_DIR=$WORK_DIR/log;export LOG_DIR

# Where the scripts we use in training are located
TRAIN_SCRIPTS=$HOME_DIR/bin;export TRAIN_SCRIPTS

# Directory that holds common things used in training
TRAIN_COMMON=$HOME_DIR/common;export TRAIN_COMMON

# This should be set to split the training data into about 1 hour chunks.
HEREST_SPLIT=10;export HEREST_SPLIT

# Causes training to be split among multiple threads (for multi-core
# machines), you'll need to have enough memory as well.
HEREST_THREADS=10;export HEREST_THREADS

# Size of the reduced training set
N_TRAIN_FILES=500000;export N_TRAIN_FILES

# Triphone state clustering
RO=100;export RO
TB=350;export TB

# Word penalty and language model scaling factors
IP=-0.0;export IP
SFZ=8.0;export SFZ
SFB=8.0;export SFB
SFT=8.0;export SFT

# Train cross word triphone models or word internal triphone models?
#CROSS=cross;export CROSS
CROSS=wit;export CROSS

