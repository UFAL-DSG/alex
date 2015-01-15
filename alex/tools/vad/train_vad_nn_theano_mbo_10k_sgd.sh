#!/bin/sh
#

DEV='gpu0'
EP='100'
MF='10000'
MFS='10k'

BS='1000'
BSS='1k'

PF=15
NF=15

HU=32
HL=1
HLA=3

ACF=4.0

M='sg-fixedlr'
A='tanh'

export THEANO_FLAGS=mode=FAST_RUN,device=$DEV,floatX=float32
export THEANO_FLAGS=device=$DEV,floatX=float32,profile=True,profile_memmory=True
export CUDA_LAUNCH_BLOCKING=1
nohup ./train_vad_nn_theano.py --max_epoch $EP --method $M --hact $A --batch_size $BS --max_frames $MF --hidden_units $HU --hidden_layers $HL --hidden_layers_add $HLA --prev_frames $PF --next_frames $NF --amplify_center_frame $ACF --mel_banks_only 1 > log.nnt_mf_$MFS.hu_$HU.hl_$HL.hla_$HLA.pf_$PF.nf_$NF.acf_$ACF.mbo.bs_$BSS.$M.$A &


