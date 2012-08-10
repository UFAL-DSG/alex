#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from multiprocessing import *
from sklearn import mixture
from scipy.misc import logsumexp
from collections import deque

import __init__

from SDS.ml.gmm import GMM
from SDS.utils.htk import *

train_data = 'asr_model_voip_en/train/*.mfc'
train_data_aligned = 'asr_model_voip_en/aligned_best.mlf'

filter_length = 5
prob_speech_up = 0.3
prob_speech_stay = 0.1

max_files = 100

mlf = MLF(train_data_aligned, max_files = max_files)
mlf.filter_zero_segments()
# map all sp, _noise_, _laugh_, _inhale_ to sil
mlf.sub('sp', 'sil')
mlf.sub('_noise_', 'sil')
mlf.sub('_laugh_', 'sil')
mlf.sub('_inhale_', 'sil')
# map everything except of sil to speech
mlf.sub('sil', 'speech', False)
mlf.merge()
#mlf.times_to_seconds()
mlf.times_to_frames()
#mlf.trim_segments(3)

print "The length of sil segments:    ", mlf.count_length('sil')
print "The length of speech segments: ", mlf.count_length('speech')

print '-'*120
print 'VAD GMM test'
print '-'*120
gmm_speech = GMM(n_features = 0)
gmm_speech.load_model('vad_speech_wav.gmm')
gmm_sil = GMM(n_features = 0)
gmm_sil.load_model('vad_sil_wav.gmm')

vta = MLFFeaturesAlignedArray()
vta.append_mlf(mlf)
vta.append_trn(train_data)

accuracy = 0.0
n = 0
log_probs_speech = deque(maxlen = filter_length)
log_probs_sil = deque(maxlen = filter_length)

prev_rec_label = 'sil'

for frame, label in vta:
  log_prob_speech = gmm_speech.score(frame)
  log_prob_sil = gmm_sil.score(frame)

  log_probs_speech.append(log_prob_speech)
  log_probs_sil.append(log_prob_sil)

  log_prob_speech_avg = 0.0
  for log_prob_speech, log_prob_sil in zip(log_probs_speech, log_probs_sil):
    log_prob_speech_avg += log_prob_speech - logsumexp([log_prob_speech, log_prob_sil])
  log_prob_speech_avg /= float(filter_length)

  if prev_rec_label == 'sil':
    if log_prob_speech_avg >= np.log(prob_speech_up):
      rec_label = 'speech'
    else:
      rec_label = 'sil'
  elif prev_rec_label == 'speech':
    if log_prob_speech_avg >= np.log(prob_speech_stay):
      rec_label = 'speech'
    else:
      rec_label = 'sil'

  prev_rec_label = rec_label
#  print rec_label

  if rec_label == label:
    accuracy += 1.0

  n += 1

accuracy = accuracy*100.0/n

print "VAD accuracy : %0.3f%% " % accuracy
