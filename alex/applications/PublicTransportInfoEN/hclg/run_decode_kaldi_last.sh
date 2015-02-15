#!/bin/bash

time ../../../corpustools/asr_decode.py -c kaldi_last.cfg -n 15 -f -o decoded_kaldi_last  load ../lm/reference_transcription_dev.txt
