#!/bin/sh
## Fail: python.sh
#

for M in sg-rprop
do
    for A in relu softplus sigmoid tanh
    do
        #nohup ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch 15 --method $M --hact $A --batch_size 10000 --max_frames 1000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1k_hu_32_lf_0_c0_0.$M.$A &
        #nohup ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch 15 --method $M --hact $A --batch_size 10000 --max_frames 1000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1M_hu_32_lf_0_c0_0.$M.$A &
        nohup ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch 15 --method $M --hact $A --batch_size 10000 --max_frames 100000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_100M_hu_32_lf_0_c0_0.$M.$A &
        echo "." && sleep 20
    done
    wait
done

for M in ng-fixedlr
do
    for A in relu softplus sigmoid tanh 
    do
        #nohup ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch 15 --method $M --hact $A --batch_size 10000 --max_frames 1000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1k_hu_32_lf_0_c0_0.$M.$A &
        #nohup ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch 15 --method $M --hact $A --batch_size 10000 --max_frames 1000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1M_hu_32_lf_0_c0_0.$M.$A &
        nohup ./train_voip_en_nn_theano_sds_mfcc.py --max_epoch 15 --method $M --hact $A --batch_size 10000 --max_frames 100000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_100M_hu_32_lf_0_c0_0.$M.$A &
        echo "." && sleep 20
        wait
    done
done

