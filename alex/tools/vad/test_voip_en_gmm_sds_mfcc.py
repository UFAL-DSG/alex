#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import datetime

from multiprocessing import *
from scipy.misc import logsumexp
from collections import deque

if __name__ == "__main__":
    import autopath
import __init__

from alex.ml.gmm import GMM
from alex.utils.htk import *

train_data = 'data_voip_en/train/*.wav'
train_data_aligned = 'asr_model_voip_en/aligned_best.mlf'

n_max_frames = 200000

filter_length = 1  # 5
prob_speech_up = 0.5  # 0.3
prob_speech_stay = 0.5  # 0.1

max_files = 100000
max_frames_per_segment = 50  # 0
trim_segments = 0

train_data_sil = 'data_vad_sil/data/*.wav'
train_data_sil_aligned = 'data_vad_sil/vad-silence.mlf'


def load_mlf(train_data_sil_aligned, max_files, max_frames_per_segment):
    mlf_sil = MLF(train_data_sil_aligned, max_files=max_files)
    mlf_sil.filter_zero_segments()
    # map all sp, _noise_, _laugh_, _inhale_ to sil
    mlf_sil.sub('sp', 'sil')
    mlf_sil.sub('_noise_', 'sil')
    mlf_sil.sub('_laugh_', 'sil')
    mlf_sil.sub('_inhale_', 'sil')
    # map everything except of sil to speech
    mlf_sil.sub('sil', 'speech', False)
    mlf_sil.merge()
    #mlf_sil.times_to_seconds()
    mlf_sil.times_to_frames()
    mlf_sil.trim_segments(trim_segments)
    mlf_sil.shorten_segments(max_frames_per_segment)

    return mlf_sil

train_data_sil = 'data_vad_sil/data/*.wav'
train_data_sil_aligned = 'data_vad_sil/vad-silence.mlf'

train_data_speech = 'data_voip_en/train/*.wav'
train_data_speech_aligned = 'asr_model_voip_en/aligned_best.mlf'

mlf_sil = load_mlf(train_data_sil_aligned, max_files, max_frames_per_segment)
mlf_speech = load_mlf(
    train_data_speech_aligned, max_files, max_frames_per_segment)

print datetime.datetime.now()
# print "The length of sil segments in sil:    ", mlf_sil.count_length('sil')
# print "The length of speech segments in sil: ", mlf_sil.count_length('speech')
print "The length of sil segments in speech:    ", mlf_speech.count_length(
    'sil')
print "The length of speech segments in speech: ", mlf_speech.count_length(
    'speech')


print '-' * 120
print 'VAD GMM test'
print datetime.datetime.now()
print '-' * 120
gmm_speech = GMM(n_features=0)
gmm_speech.load_model('model_voip_en/vad_speech_sds_mfcc.gmm')
gmm_sil = GMM(n_features=0)
gmm_sil.load_model('model_voip_en/vad_sil_sds_mfcc.gmm')

vta = MLFMFCCOnlineAlignedArray(usec0=False)
# vta.append_mlf(mlf_sil)
# vta.append_trn(train_data_sil)
vta.append_mlf(mlf_speech)
vta.append_trn(train_data_speech)

print "Generating the MFCC features"
vta_new = []
i = 0
for frame, label in vta:
    if i % (n_max_frames / 10) == 0:
        print "Already processed: %.2f%% of data" % (100.0*i/n_max_frames)

    if i > n_max_frames:
        break
    i += 1

    vta_new.append((frame, label))
vta = vta_new

print "Length of test data:", len(vta)
print datetime.datetime.now()

accuracy = 0.0
n = 0
log_probs_speech = deque(maxlen=filter_length)
log_probs_sil = deque(maxlen=filter_length)

prev_rec_label = 'sil'

for frame, label in vta:
    log_prob_speech = gmm_speech.score(frame)
    log_prob_sil = gmm_sil.score(frame)

    log_probs_speech.append(log_prob_speech)
    log_probs_sil.append(log_prob_sil)

    log_prob_speech_avg = 0.0
    for log_prob_speech, log_prob_sil in zip(log_probs_speech, log_probs_sil):
        log_prob_speech_avg += log_prob_speech - logsumexp(
            [log_prob_speech, log_prob_sil])
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

accuracy = accuracy * 100.0 / n

print "VAD accuracy : %0.3f%% " % accuracy
print datetime.datetime.now()
