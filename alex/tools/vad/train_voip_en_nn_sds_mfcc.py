#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import datetime

from collections import deque

from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure import TanhLayer, SigmoidLayer, SoftmaxLayer
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer, RPropMinusTrainer

import __init__

from alex.utils.htk import *

max_files = 100#0000
max_frames_per_segment = 50#50
trim_segments = 0 #30
n_max_epoch = 10000
n_max_frames_per_minibatch = 500
n_hidden_units = 128
sigmoid = True
arac = True
n_last_frames = 0
n_crossvalid_minibatches = max_files / 20

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


def get_accuracy(ds, a):
    """ Compute accuracy of predictions from the activation of the last NN layer, and the sil prior probability.

    :param ds: the training dataset
    :param a: activation from the NN using the ds datasat
    """
    n = 0
    acc = 0
    sil = 0
    for g, p in zip(ds, a):
        #print g[1][0], p[0]
        n += 1.0
        acc += 1.0 if ((g[1][0] > 0.5) and (p[0] > 0.5)) or ((g[1][0] <= 0.5) and (p[0] <= 0.5)) else 0.0
        sil += 1.0 if g[1][0] < 0.5 else 0.0

    return acc/n*100, sil/n*100

def running_avg(avg, n, value):
    return (float(avg)*n + float(value))/ (n+1)

def train_nn():
    vta = MLFMFCCOnlineAlignedArray(usec0=False, n_last_frames=n_last_frames)
    # vta.append_mlf(mlf_sil)
    # vta.append_trn(train_data_sil)
    vta.append_mlf(mlf_speech)
    vta.append_trn(train_data_speech)

    mfcc = vta.__iter__().next()

    print "MFCC length:", len(mfcc[0])
    input_size = len(mfcc[0])

    if sigmoid:
        net = buildNetwork(input_size,n_hidden_units,n_hidden_units,n_hidden_units,n_hidden_units,2, hiddenclass=SigmoidLayer, outclass=SoftmaxLayer,
                           bias = True, fast = arac)
    else:
        net = buildNetwork(input_size,n_hidden_units,n_hidden_units,n_hidden_units,n_hidden_units,2, hiddenclass=TanhLayer, outclass=SoftmaxLayer,
                           bias = True, fast = arac)

    dc_acc = deque(maxlen=20)
    dt_acc = deque(maxlen=20)

    for epoch in range(n_max_epoch):
        i = 1
        m = 0
        ds = SupervisedDataSet(input_size, 2)

        c_acc = 0.0
        c_sil = 0.0
        t_acc = 0.0
        t_sil = 0.0

        for frame, label in vta:
            #print frame
            if (i % n_max_frames_per_minibatch) != 0:
                if label == "sil":
                    ds.addSample(frame, (1,0))
                else:
                    ds.addSample(frame, (0,1))
            else:
                a = net.activateOnDataset(ds)
                acc, sil = get_accuracy(ds, a)

                print
                print "-"*120
                if m < n_crossvalid_minibatches:
                    print "Cross-validation"

                    c_acc = running_avg(c_acc, m, acc)
                    c_sil = running_avg(c_sil, m, sil)

                else:
                    print "Training"
                    t_acc = running_avg(t_acc, m, acc)
                    t_sil = running_avg(t_sil, m, sil)

                    trainer = BackpropTrainer(net, ds)
                    trainer.train()

                m += 1


                print
                print "max_files, max_frames_per_segment, trim_segments, n_max_epoch, n_max_frames_per_minibatch, n_hidden_units, sigmoid, arac, n_last_frames, n_crossvalid_minibatches"
                print max_files, max_frames_per_segment, trim_segments, n_max_epoch, n_max_frames_per_minibatch, n_hidden_units, sigmoid, arac, n_last_frames, n_crossvalid_minibatches
                print "Epoch: %d Mini-batch: %d" % (epoch, m)
                print
                print "Cross-validation stats"
                print "------------------------"
                print "Epoch predictive accuracy:  %0.2f" % c_acc
                print "Last epoch accs:", ["%.2f" % x for x in dc_acc]
                print "Epoch sil bias: %0.2f" % c_sil
                print
                print "Training stats"
                print "------------------------"
                print "Epoch predictive accuracy:  %0.2f" % t_acc
                print "Last epoch accs:", ["%.2f" % x for x in dt_acc]
                print "Epoch sil bias: %0.2f" % t_sil

                print
                print "Minibatch stats"
                print "------------------------"
                print "Mini-batch predictive accuracy: %0.2f" % acc
                print "Mini-batch sil bias: %0.2f" % sil


                ds = SupervisedDataSet(input_size, 2)

            i += 1

        dc_acc.append(c_acc)
        dt_acc.append(t_acc)


##################################################

#train_data_sil = 'data_vad_sil/data/*.wav'
#train_data_sil_aligned = 'data_vad_sil/vad-silence.mlf'

train_data_speech = 'data_voip_en/train/*.wav'
train_data_speech_aligned = 'asr_model_voip_en/aligned_best.mlf'

#mlf_sil = load_mlf(train_data_sil_aligned, max_files, max_frames_per_segment)
mlf_speech = load_mlf(train_data_speech_aligned, max_files, max_frames_per_segment)

print datetime.datetime.now()
# print "The length of sil segments in sil:    ", mlf_sil.count_length('sil')
# print "The length of speech segments in sil: ", mlf_sil.count_length('speech')
print "The length of sil segments in speech:    ", mlf_speech.count_length('sil')
print "The length of speech segments in speech: ", mlf_speech.count_length('speech')


train_nn()

