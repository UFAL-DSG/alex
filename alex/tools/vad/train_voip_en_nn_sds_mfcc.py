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

max_files = 100#0000
max_frames_per_segment = 50#50
trim_segments = 0 #30
n_iter = 10000
n_minibatch = 500
lsize = 128
sigmoid = True
fast = True
n_last_frames = 20

alpha = 0.995

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
    vta = MLFMFCCOnlineAlignedArray(usec0=False, n_last_frames=n_last_frames)
    vta.append_mlf(mlf_sil)
    vta.append_trn(train_data_sil)
    vta.append_mlf(mlf_speech)
    vta.append_trn(train_data_speech)

    #vta = list(vta)[::2]
    mfcc = vta.__iter__().next()

    print "MFCC length:", len(mfcc[0])
    input_size = len(mfcc[0])

    if sigmoid:
        net = buildNetwork(input_size,lsize,lsize,lsize,lsize,2, hiddenclass=SigmoidLayer, outclass=SoftmaxLayer,
                           bias = True, fast = fast)
    else:
        net = buildNetwork(input_size,lsize,lsize,lsize,lsize,2, hiddenclass=TanhLayer, outclass=SoftmaxLayer,
                           bias = True, fast = fast)

    cgavg = 0.0
    for nn in range(n_iter):
        i = 1
        m = 0
        ds = SupervisedDataSet(input_size, 2)
        for frame, label in vta:
            #print frame
            if (i % n_minibatch) != 0:
                if label == "sil":
                    ds.addSample(frame, (1,0))
                else:
                    ds.addSample(frame, (0,1))
            else:
                m += 1
                a = net.activateOnDataset(ds)

                n = 0
                c = 0
                gg = 0
                for g, p in zip(ds, a):
                    #print g[1][0], p[0]
                    n += 1
                    c += 1 if ((g[1][0] > 0.5) and (p[0] > 0.5)) or ((g[1][0] <= 0.5) and (p[0] <= 0.5)) else 0
                    gg += 1 if g[1][0] < 0.5 else 0

                cgavg = alpha*cgavg + (1-alpha)*float(c)/n*100
                print
                print "max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames"
                print max_files, max_frames_per_segment, trim_segments, n_iter, n_minibatch, lsize, sigmoid, fast, n_last_frames
                print "N-iter: %d Mini-batch: %d" % (nn, m)
                print "Geometric predictive accuracy:  %0.2f" % cgavg
                print "Mini-batch predictive accuracy: %0.2f" % (float(c)/n*100)
                print "Mini-batch sil bias: %0.2f" % (float(gg)/n*100)

                trainer = BackpropTrainer(net, ds)
                print trainer.train()


                ds = SupervisedDataSet(input_size, 2)

            i += 1

##################################################

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
