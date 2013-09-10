#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import datetime
import glob

from scipy.misc import logsumexp
from collections import deque

import autopath

from alex.ml.ffnn import FFNN
from alex.utils.htk import *

train_data = 'data_voip_en/train/*.wav'
train_data_aligned = 'asr_model_voip_en/aligned_best.mlf'

n_max_frames = 200000

max_files = 100000
max_frames_per_segment = 50
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
mlf_speech = load_mlf(train_data_speech_aligned, max_files, max_frames_per_segment)

print datetime.datetime.now()
# print "The length of sil segments in sil:    ", mlf_sil.count_length('sil')
# print "The length of speech segments in sil: ", mlf_sil.count_length('speech')
print "The length of sil segments in speech:    ", mlf_speech.count_length('sil')
print "The length of speech segments in speech: ", mlf_speech.count_length('speech')


print '-' * 120
print 'VAD FFNN test'
print datetime.datetime.now()
print '-' * 120

nnfn = []
nns = []
for fn in glob.glob('model_voip_en/*.nn'):
    nn = FFNN()
    nn.load(fn)
    nns.append(nn)

    nnfn.append(fn)

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

nn_acc = [0.0,]*len(nns)
n = 0

for frame, label in vta:
    for i, nn in enumerate(nns):
        p = nn.predict(frame)

        if (p[0] > 0.5 and label == 'sil') or (p[0] < 0.5 and label != 'sil'):
            nn_acc[i] += 1

    n += 1

for i, nn in enumerate(nns):
    print "VAD accuracy %s: %0.3f%% " % (nnfn[i], nn_acc[i]*100.0/n)

print datetime.datetime.now()
