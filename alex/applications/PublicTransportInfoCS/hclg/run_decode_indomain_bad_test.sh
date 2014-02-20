#!/bin/bash

python download_models.py

./decode_indomain.py -f -c kaldi_slow.cfg -o decode_indomain_test  load ./reference_transcription_test_bad.txt 
