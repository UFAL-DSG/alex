#!/bin/bash

time ./decode_indomain.py -c kaldi_tri2b_bmmi.cfg -f -o decoded_kaldi  load ../lm/reference_transcription_dev.txt
