#!/bin/sh
## Fail: python.sh
#

for M in sg-fixedlr sg-rprop sg-adalr
do
    for A in tanh sigmoid softplus relu
    do
        #nohup ./train_voip_en_nn_theano_sds_mfcc.py --method $M --hact $A --batch_size 20000 --max_frames 1000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1k_hu_32_lf_0_c0_0.$M.$A &
        nohup ./train_voip_en_nn_theano_sds_mfcc.py --method $M --hact $A --batch_size 20000 --max_frames 1000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1M_hu_32_lf_0_c0_0.$M.$A &
        echo "." && sleep 20
    done
    wait
done

for M in ng-fixedlr ng-rprop ng-adalr
do
    for A in tanh sigmoid softplus relu
    do
        #nohup ./train_voip_en_nn_theano_sds_mfcc.py --method $M --hact $A --batch_size 20000 --max_frames 1000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1k_hu_32_lf_0_c0_0.$M.$A &
        nohup ./train_voip_en_nn_theano_sds_mfcc.py --method $M --hact $A --batch_size 20000 --max_frames 1000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nnt_mf_1M_hu_32_lf_0_c0_0.$M.$A &
        echo "." && sleep 20
        wait
    done
done

