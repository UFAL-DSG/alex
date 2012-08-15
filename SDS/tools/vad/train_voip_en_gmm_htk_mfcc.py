#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from multiprocessing import *
from sklearn import mixture

import __init__

from SDS.ml.gmm import GMM

#from SDS.components.vad import GMMVAD
from SDS.utils.htk import *

train_data = 'asr_model_voip_en/train/*.mfc'
train_data_aligned = 'asr_model_voip_en/aligned_best.mlf'

max_files = 10
n_iter = 10
n_mixies = 16

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
mlf.trim_segments(3)

print "The length of sil segments:    ", mlf.count_length('sil')
print "The length of speech segments: ", mlf.count_length('speech')

def train_speech_gmm():
  vta_speech = MLFFeaturesAlignedArray(filter='speech')
  vta_speech.append_mlf(mlf)
  vta_speech.append_trn(train_data)

  data_speech = vta_speech

  gmm_speech = GMM(n_features = 39, n_components = 1, n_iter = n_iter)
  gmm_speech.fit(data_speech)
  for i in range(n_mixies):
    gmm_speech.mixup(1)
    gmm_speech.fit(data_speech)
    print "Speech weights:"
    print gmm_speech.weights
    print "Speech LP:", gmm_speech.log_probs[-1]
    print "-"*120
  gmm_speech.save_model('model_voip_en/vad_speech_htk_mfcc.gmm')
  return

def train_sil_gmm():
  vta_sil = MLFFeaturesAlignedArray(filter='sil')
  vta_sil.append_mlf(mlf)
  vta_sil.append_trn(train_data)

  data_sil = vta_sil

  gmm_sil = GMM(n_features = 39, n_components = 1, n_iter = n_iter)
  gmm_sil.fit(data_sil)
  for i in range(n_mixies):
    gmm_sil.mixup(1)
    gmm_sil.fit(data_sil)
    print "Sil weights:"
    print gmm_sil.weights
    print "Sil LP:", gmm_sil.log_probs[-1]
    print "-"*120
  gmm_sil.save_model('model_voip_en/vad_sil_htk_mfcc.gmm')

p_speech = Process(target=train_speech_gmm)
p_sil = Process(target=train_sil_gmm)
p_speech.start()
p_sil.start()

p_sil.join()
print "Sil GMM training finished"
p_speech.join()
print "Speech GMM training finished"


print '-'*120
print 'VAD GMM test'
print '-'*120
gmm_speech = GMM(n_features = 0)
gmm_speech.load_model('model_voip_en/vad_speech_htk_mfcc.gmm')
gmm_sil = GMM(n_features = 0)
gmm_sil.load_model('model_voip_en/vad_sil_htk_mfcc.gmm')


vta = MLFFeaturesAlignedArray()
vta.append_mlf(mlf)
vta.append_trn(train_data)

accuracy = 0.0
n = 0
for frame, label in vta:
  log_prob_speech = gmm_speech.score(frame)
  log_prob_sil = gmm_sil.score(frame)

  ratio = log_prob_speech - log_prob_sil
  if ratio >= 0:
    rec_label = 'speech'
  else:
    rec_label = 'sil'

  if rec_label == label:
    accuracy += 1.0

  n += 1

accuracy = accuracy*100.0/n

print "VAD accuracy : %0.3f%% " % accuracy
