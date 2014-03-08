#!/bin/bash
if [ "$#" != 1 ]; then
    echo "Usage: $0 <train-data-portion>"
    echo "Must be run from within PTICS directory on testing_acl"
    exit 1
fi

ln -s /net/projects/vystadial/data/call-logs/2013-05-30-alex-aotb-prototype/total lm/indomain_data
ln -s /net/projects/vystadial/data/call-logs/2013-05-30-alex-aotb-prototype/total slu/indomain_data

set -e  # exit on any command fail

cd data
echo -e `date` '***********************************\nDATABASE DUMP' | tee -a ../training-log-noshuffle.txt
./database.py dump

cd ../lm
echo -e `date` '***********************************\nBUILDING LM' | tee -a ../training-log-noshuffle.txt
./build.py --train-limit $1 --noshuffle >> ../training-log-noshuffle.txt 2>&1

cd ../hclg
echo -e `date` '***********************************\nBUILDING HCLG' | tee -a ../training-log-noshuffle.txt
./run_build_hclg.sh >> ../training-log-noshuffle.txt 2>&1

echo -e `date` '***********************************\nRUNNING DECODE' | tee -a ../training-log-noshuffle.txt
./run_decode_indomain_kaldi.sh >> ../training-log-noshuffle.txt 2>&1

cd ../slu
echo -e `date` '***********************************\nPREPARING SLU DATA' | tee -a ../training-log-noshuffle.txt
./prepare_data.py --train-limit $1 --noshuffle >> ../training-log-noshuffle.txt 2>&1

