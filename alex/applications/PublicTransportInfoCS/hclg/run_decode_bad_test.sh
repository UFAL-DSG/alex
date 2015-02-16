#!/bin/bash

python download_models.py

time ../../../corpustools/asr_decode.py -f -c kaldi_slow.cfg -o decode_indomain_test  load ./reference_transcription_test_bad.txt
