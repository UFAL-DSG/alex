#!/bin/sh
## Fail: python.sh
#

DEV='gpu'
EP='1000'
MF='30000000'
MFS='30M'

BS='50000'
BSS='50k'

LF=0
PF=0

M='sg-fixedlr'
A='tanh'

export THEANO_FLAGS=mode=FAST_RUN,device=$DEV,floatX=float32
nohup  ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch $EP --method $M --hact $A --batch_size $BS --max_frames $MF --hidden_units 32 --last_frames $LF --prev_frames $PF --mel_banks_only 1 > log.nnt_mf_$MFS.hu_32_lf_$LF.pf_$PF.mbo.bs_$BSS.$M.$A &



