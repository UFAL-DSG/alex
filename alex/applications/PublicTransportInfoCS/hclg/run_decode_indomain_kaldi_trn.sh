#!/bin/bash

time ./decode_indomain.py -c kaldi.cfg -f -o decoded_kaldi  load ../lm/reference_transcription_trn.txt
