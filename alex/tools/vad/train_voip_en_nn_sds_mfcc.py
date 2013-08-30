#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import datetime
import itertools
from multiprocessing import *

from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure import TanhLayer, SigmoidLayer, SoftmaxLayer
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer, RPropMinusTrainer

import __init__

from alex.utils.htk import *

max_files = 100#000
max_frames_per_segment = 100#000
trim_segments = 30
n_iter = 10
n_minibatch = 500

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


def train_nn():
    vta = MLFMFCCOnlineAlignedArray(usec0=False)
    vta.append_mlf(mlf_sil)
    vta.append_trn(train_data_sil)
    vta.append_mlf(mlf_speech)
    vta.append_trn(train_data_speech)

    vta = list(vta)[::2]

    net = buildNetwork(36,5,5,2, hiddenclass=TanhLayer, outclass=SoftmaxLayer)

    i = 1
    ds = SupervisedDataSet(36, 2)
    for frame, label in vta:
        if (i % n_minibatch) != 0:
            if label == "sil":
                ds.addSample(frame, (1,0))
            else:
                ds.addSample(frame, (0,1))
        else:
            #trainer = BackpropTrainer(net, ds)
            trainer = RPropMinusTrainer(net, dataset = ds)
            for n in range(1):
                print trainer.train()

            print net.activateOnDataset(ds)

            ds = SupervisedDataSet(36, 2)

        i += 1




train_data_sil = 'data_vad_sil/data/*.wav'
train_data_sil_aligned = 'data_vad_sil/vad-silence.mlf'

train_data_speech = 'data_voip_en/train/*.wav'
train_data_speech_aligned = 'asr_model_voip_en/aligned_best.mlf'

mlf_sil = load_mlf(train_data_sil_aligned, max_files, max_frames_per_segment)
mlf_speech = load_mlf(train_data_speech_aligned, max_files, max_frames_per_segment)

print datetime.datetime.now()
print "The length of sil segments in sil:    ", mlf_sil.count_length('sil')
print "The length of speech segments in sil: ", mlf_sil.count_length('speech')
print "The length of sil segments in speech:    ", mlf_speech.count_length('sil')
print "The length of speech segments in speech: ", mlf_speech.count_length('speech')


train_nn()


#print '-' * 120
#print 'VAD GMM test'
#print datetime.datetime.now()
#print '-' * 120
#gmm_speech = GMM(n_features=0)
#gmm_speech.load_model('model_voip_en/vad_speech_sds_mfcc.gmm')
#gmm_sil = GMM(n_features=0)
#gmm_sil.load_model('model_voip_en/vad_sil_sds_mfcc.gmm')
#
#vta = MLFMFCCOnlineAlignedArray(usec0=False)
#vta.append_mlf(mlf_sil)
#vta.append_trn(train_data_sil)
#vta.append_mlf(mlf_speech)
#vta.append_trn(train_data_speech)
#
#vta = list(vta)[1::2]
#
#print "Length of test data:", len(vta)
#print datetime.datetime.now()
#
#accuracy = 0.0
#n = 0
#for frame, label in vta:
#    log_prob_speech = gmm_speech.score(frame)
#    log_prob_sil = gmm_sil.score(frame)
#
#    ratio = log_prob_speech - log_prob_sil
#    if ratio >= 0:
#        rec_label = 'speech'
#    else:
#        rec_label = 'sil'
#
#    if rec_label == label:
#        accuracy += 1.0
#
#    n += 1
#
#accuracy = accuracy * 100.0 / n
#
#print "VAD accuracy : %0.3f%% " % accuracy
#print datetime.datetime.now()
