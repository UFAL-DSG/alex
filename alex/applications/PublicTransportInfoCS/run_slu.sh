#!/bin/bash

set -e  # exit on any command fail

cd slu
echo -e `date` '***********************************\nTRAINING SLU' | tee -a ../training-log.txt
./train.py >> ../training-log.txt 2>&1

echo -e `date` '***********************************\nTESTING SLU' | tee -a ../training-log.txt
./test.py >> ../training-log.txt 2>&1
echo -e `date` '***********************************\nTESTING SLU (BOOTSTRAP)' | tee -a ../training-log.txt
./test_bootstrap.py >> ../training-log.txt 2>&1

echo -e `date` '***********************************\nDONE' | tee -a ../training-log.txt
./print_scores.sh | tee -a ../training-log.txt

