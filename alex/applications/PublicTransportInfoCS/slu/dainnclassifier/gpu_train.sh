#!/bin/sh
## Fail: python.sh
#

DEV='gpu0'

export THEANO_FLAGS=mode=FAST_RUN,device=$DEV,floatX=float32 #,nvcc.fastmath=True,allow_gc=False
nohup ./train.py > log.$DEV &
