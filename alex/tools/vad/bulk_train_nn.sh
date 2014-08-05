#!/bin/sh
## Fail: python.sh
#

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nn_mf_100M_hu_32_lf_0_c0_0 &
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000000 --hidden_units 32 --last_frames 3 --usec0 0 --mel_banks_only 0 > log.nn_mf_100M_hu_32_lf_3_mfc &
#echo "." && sleep 20
nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 10000 --hidden_units 32 --last_frames 3 --usec0 0 --mel_banks_only 1 > log.nn_mf_100M_hu_32_lf_3_mbo &
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000000 --hidden_units 32 --last_frames 3 --usec0 0 --mel_banks_only 1 > log.nn_mf_100M_hu_32_lf_3_mbo &
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000000 --hidden_units 32 --last_frames 6 --usec0 0 --mel_banks_only 1 > log.nn_mf_100M_hu_32_lf_6_mbo &
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000000 --hidden_units 32 --last_frames 9 --usec0 0 --mel_banks_only 1 > log.nn_mf_100M_hu_32_lf_9_mbo &


#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --preconditioner 0 > log.nn_mf_100k_hu_64_lf_0_c0_0_pc0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --preconditioner 1 > log.nn_mf_100k_hu_64_lf_0_c0_0_pc1 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --weight_l2 0.0001 > log.nn_mf_100k_hu_64_lf_0_c0_0_l2_0.0001 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --weight_l2 0.001 > log.nn_mf_100k_hu_64_lf_0_c0_0_l2_0.001 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --weight_l2 0.10 > log.nn_mf_100k_hu_64_lf_0_c0_0_l2_0.10 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --weight_l2 0.20 > log.nn_mf_100k_hu_64_lf_0_c0_0_l2_0.20_b & 
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --hidden_dropouts 0.3 > log.nn_mf_100k_hu_64_lf_0_c0_0_hd_0.3 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --hidden_dropouts 0.5 > log.nn_mf_100k_hu_64_lf_0_c0_0_hd_0.5 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 --hidden_dropouts 0.7 > log.nn_mf_100k_hu_64_lf_0_c0_0_hd_0.7 &
#echo "." && sleep 20


# Tests without MFCC C0
#-----------------------------

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nn_mf_100k_hu_32_lf_0_c0_0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 32 --last_frames 10 --usec0 0 > log.nn_mf_100k_hu_32_lf_10_c0_0 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 0 > log.nn_mf_100k_hu_64_lf_0_c0_0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 10 --usec0 0 > log.nn_mf_100k_hu_64_lf_10_c0_0 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nn_mf_1M_hu_32_lf_0_c0_0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 32 --last_frames 10 --usec0 0 > log.nn_mf_1M_hu_32_lf_10_c0_0 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 64 --last_frames 0 --usec0 0 > log.nn_mf_1M_hu_64_lf_0_c0_0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 64 --last_frames 10 --usec0 0 > log.nn_mf_1M_hu_64_lf_10_c0_0 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 5000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nn_mf_5M_hu_32_lf_0_c0_0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 5000000 --hidden_units 32 --last_frames 10 --usec0 0 > log.nn_mf_5M_hu_32_lf_10_c0_0 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 15000000 --hidden_units 32 --last_frames 0 --usec0 0 > log.nn_mf_15M_hu_32_lf_0_c0_0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 15000000 --hidden_units 32 --last_frames 10 --usec0 0 > log.nn_mf_15M_hu_32_lf_10_c0_0 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 15000000 --hidden_units 64 --last_frames 0 --usec0 0 > log.nn_mf_15M_hu_64_lf_0_c0_0 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 15000000 --hidden_units 64 --last_frames 10 --usec0 0 > log.nn_mf_15M_hu_64_lf_10_c0_0 &
#echo "." && sleep 20


# Tests with MFCC C0
#----------------------------

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 32 --last_frames 0 --usec0 1 > log.nn_mf_100k_hu_32_lf_0_c0_1 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 32 --last_frames 10 --usec0 1 > log.nn_mf_100k_hu_32_lf_10_c0_1 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 0 --usec0 1 > log.nn_mf_100k_hu_64_lf_0_c0_1 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 100000 --hidden_units 64 --last_frames 10 --usec0 1 > log.nn_mf_100k_hu_64_lf_10_c0_1 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 32 --last_frames 0 --usec0 1 > log.nn_mf_1M_hu_32_lf_0_c0_1 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 32 --last_frames 10 --usec0 1 > log.nn_mf_1M_hu_32_lf_10_c0_1 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 64 --last_frames 0 --usec0 1 > log.nn_mf_1M_hu_64_lf_0_c0_1 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 1000000 --hidden_units 64 --last_frames 10 --usec0 1 > log.nn_mf_1M_hu_64_lf_10_c0_1 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 5000000 --hidden_units 32 --last_frames 0 --usec0 1 > log.nn_mf_5M_hu_32_lf_0_c0_1 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 5000000 --hidden_units 32 --last_frames 10 --usec0 1 > log.nn_mf_5M_hu_32_lf_10_c0_1 &
#echo "." && sleep 20

#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 15000000 --hidden_units 32 --last_frames 0 --usec0 1 > log.nn_mf_15M_hu_32_lf_0_c0_1 &
#echo "." && sleep 20
#nohup ./train_voip_en_nn_theanets_sds_mfcc.py --max_frames 15000000 --hidden_units 32 --last_frames 10 --usec0 1 > log.nn_mf_15M_hu_32_lf_10_c0_1 &
#echo "." && sleep 20

