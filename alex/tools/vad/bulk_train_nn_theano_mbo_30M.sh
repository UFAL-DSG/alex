#!/bin/sh
## Fail: python.sh
#

 
EP='1000'
MF='100000000'
MFS='100M'

LF=9

M='sg-rprop'
A='tanh'

#nohup ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch $EP --method $M --hact $A --batch_size 100000 --max_frames $MF --hidden_units 32 --last_frames $LF --mel_banks_only 1 > log.nnt_mf_$MFS.hu_32_lf_$LF.mbo.$M.$A &

EP='1000'
MF='100000000'
MFS='100M'

LF=3

M='sg-rprop'
A='tanh'

export THEANO_FLAGS=mode=FAST_RUN,device=gpu,floatX=float32
nohup  ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch $EP --method $M --hact $A --batch_size 100000 --max_frames $MF --hidden_units 32 --last_frames $LF --mel_banks_only 1 > log.nnt_mf_$MFS.hu_32_lf_$LF.mbo.$M.$A &



