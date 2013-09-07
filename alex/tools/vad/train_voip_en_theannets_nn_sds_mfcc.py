#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import datetime

from collections import deque

import __init__

from alex.utils.htk import *
import lmj.cli
import theanets

lmj.cli.enable_default_logging()

n_max_frames = 5000000
max_files = 1000000
max_frames_per_segment = 50#50
trim_segments = 0 #30
n_max_epoch = 10000
n_hidden_units = 128
n_last_frames = 0
n_crossvalid_frames = int((0.20 * n_max_frames ))  # cca 20 % of all training data

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
    n = 0.0
    acc = 0.0
    sil = 0.0
    for y, p in zip(ds, a):
        n += 1.0

        acc += 1.0 if (y == 0 and (p[0] > 0.5)) or (y == 1 and (p[0] <= 0.5)) else 0.0
        sil += 1.0 if y == 0 else 0.0

        # print '---'
        # print n
        # print y, p
        # print acc, sil

    return acc/n*100, sil/n*100

def train_nn():
    vta = MLFMFCCOnlineAlignedArray(usec0=False, n_last_frames=n_last_frames)
    # vta.append_mlf(mlf_sil)
    # vta.append_trn(train_data_sil)
    vta.append_mlf(mlf_speech)
    vta.append_trn(train_data_speech)

    mfcc = vta.__iter__().next()

    print "MFCC length:", len(mfcc[0])
    input_size = len(mfcc[0])


    e = theanets.Experiment(theanets.Classifier,
#                            layers=(input_size, n_hidden_units, 2),
                            layers=(input_size, n_hidden_units, n_hidden_units, n_hidden_units, n_hidden_units, 2),
    #                        activation = 'tanh',
    #                        learning_rate=0.001,
    #                        learning_rate_decay=0.1,
    #                        momentum=0.1,
    #                        patience=10000,
                            optimize="hf",
                            num_updates=30,
                            validate=1,
                            initial_lambda=0.1,
    #                        tied_weights=True,
                            batch_size=500,
                            )

    print "Generating the cross-validation and train MFCC features"
    crossvalid_x = []
    crossvalid_y = []
    train_x = []
    train_y = []
    i = 0
    for frame, label in vta:
        if i % (n_max_frames / 10) == 0:
            print "Already processed: %.2f%% of data" % (100.0*i/n_max_frames)

        if i > n_max_frames:
            break

        if i < n_crossvalid_frames:
            crossvalid_x.append(frame)
            if label == "sil":
                crossvalid_y.append(0)
            else:
                crossvalid_y.append(1)
        else:
            train_x.append(frame)
            if label == "sil":
                train_y.append(0)
            else:
                train_y.append(1)

        i += 1

    crossvalid = [np.array(crossvalid_x), np.array(crossvalid_y).astype('int32')]
    train = [np.array(train_x), np.array(train_y).astype('int32')]

    # print crossvalid

    dc_acc = deque(maxlen=20)
    dt_acc = deque(maxlen=20)

    for epoch in range(n_max_epoch):
        predictions_y = e.network.predict(crossvalid_x)
        c_acc, c_sil = get_accuracy(crossvalid_y, predictions_y)
        predictions_y = e.network.predict(train_x)
        t_acc, t_sil = get_accuracy(train_y, predictions_y)

        print
        print "n_max_frames, max_files, max_frames_per_segment, trim_segments, n_max_epoch, n_hidden_units, n_last_frames, n_crossvalid_frames"
        print n_max_frames, max_files, max_frames_per_segment, trim_segments, n_max_epoch, n_hidden_units, n_last_frames, n_crossvalid_frames
        print "Epoch: %d" % (epoch,)
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

        e.run(train, crossvalid)

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

