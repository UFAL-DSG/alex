#!/bin/bash

time ../../../corpustools/asr_decode.py -c kaldi.cfg -n 12 -f -o decoded_kaldi  load ../lm/reference_transcription_trn.txt
