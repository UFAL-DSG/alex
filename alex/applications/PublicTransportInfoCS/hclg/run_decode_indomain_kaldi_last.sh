#!/bin/bash

time ./decode_indomain.py -c kaldi_last.cfg -n 15 -f -o decoded_kaldi_last  load ../lm/reference_transcription_dev.txt
