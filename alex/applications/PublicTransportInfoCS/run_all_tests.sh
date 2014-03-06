#!/bin/bash


cd data
echo -e `date` '***********************************\nDATABASE DUMP' | tee -a ../training-log.txt
./database.py dump

cd ../lm
echo -e `date` '***********************************\nBUILDING LM' | tee -a ../training-log.txt
./build.py --train-limit $1 >> ../training-log.txt 2>&1

cd ../hclg
echo -e `date` '***********************************\nBUILDING HCLG' | tee -a ../training-log.txt
./run_build_hclg.sh >> ../training-log.txt 2>&1

echo -e `date` '***********************************\nRUNNING DECODE' | tee -a ../training-log.txt
./run_decode_indomain_kaldi.sh >> ../training-log.txt 2>&1

cd ../slu
echo -e `date` '***********************************\nPREPARING SLU DATA' | tee -a ../training-log.txt
./prepare_data.py --train-limit $1 >> ../training-log.txt 2>&1


echo -e `date` '***********************************\nTRAINING SLU' | tee -a ../training-log.txt
./train.py >> ../training-log.txt 2>&1

echo -e `date` '***********************************\nTESTING SLU' | tee -a ../training-log.txt
./test.py >> ../training-log.txt 2>&1
echo -e `date` '***********************************\nTESTING SLU (BOOTSTRAP)' | tee -a ../training-log.txt
./test_bootstrap.py >> ../training-log.txt 2>&1

echo -e `date` '***********************************\nDONE' | tee -a ../training-log.txt
./print_scores.sh | tee -a ../training-log.txt
