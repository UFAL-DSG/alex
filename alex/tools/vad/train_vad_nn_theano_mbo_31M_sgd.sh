#!/bin/sh
## Fail: python.sh
#

DEV='gpu0'
EP='1000'
MF='31000000'
MFS='31M'

BS='1000'
BSS='1k'

PF=30
NF=15

HU=512
HL=1
HLA=3

ACF=4.0

M='sg-fixedlr'
A='tanh'

export THEANO_FLAGS=mode=FAST_RUN,device=$DEV,floatX=float32 #,nvcc.fastmath=True,allow_gc=False
nohup ./train_vad_nn_theano.py --max_epoch $EP --method $M --hact $A --batch_size $BS --max_frames $MF --hidden_units $HU --hidden_layers $HL --hidden_layers_add $HLA --prev_frames $PF --next_frames $NF --amplify_center_frame $ACF --mel_banks_only 1 > log.nnt_mf_$MFS.hu_$HU.hl_$HL.hla_$HLA.pf_$PF.nf_$NF.acf_$ACF.mbo.bs_$BSS.$M.$A &
