#!/bin/bash

echo 'This sets "optimal" parameters for VAD'
echo 'Preference is to reduce FALSE NEGATIVES (FN)  VAD sais noise but it is speech'
echo 'FP (VAD sais speech but is noise) are quite ok but running ASR on noise cost money + time' 
echo 'The accuracy is measured using Pykaldi ASR on whole utterances vs VAD ASR utterances'  
echo 'The "recall" will be measured using the RTF on the utterances with silence and noise'
echo 'The goal is to achieve almost RTF(VAD_&_ASR) = |noise| / (|noise|+|speech|) * RTF(ASR) and WER(VAD_&_ASR) = WER(ASR)'
