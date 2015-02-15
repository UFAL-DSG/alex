#!/usr/bin/env python
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import autopath

import numpy as np
import datetime
from multiprocessing import *


from alex.ml.gmm import GMM
from alex.utils.htk import *

n_max_frames = 5000000
n_crossvalid_frames = int((0.20 * n_max_frames ))  # cca 20% of all training data

max_files = 100000
max_frames_per_segment = 50
trim_segments = 0
n_iter = 10
n_mixies = 64 # 32 # 16


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


def mixup(gmm, vta, name):
    i = len(gmm.weights)

    if i >= 256:
        gmm.mixup(12)
    if i >= 128:
        gmm.mixup(10)
    if i >= 64:
        gmm.mixup(8)
    elif i >= 32:
        gmm.mixup(6)
    elif i >= 16:
        gmm.mixup(4)
    elif i >= 8:
        gmm.mixup(2)
    else:
        gmm.mixup(1)

    gmm.fit(vta)
    print "%s weights: %d" % (name, len(gmm.weights))
    print gmm.weights
    print "%s LP: %f" % (name, gmm.log_probs[-1])
    print datetime.datetime.now()
    print "-" * 120


def train_gmm(name, vta):

    vta = [frame for frame, label in vta if label == name]

    gmm = GMM(n_features=36, n_components=1, n_iter=n_iter)
    gmm.fit(vta)
    while len(gmm.weights) < n_mixies:
        mixup(gmm, vta, name)
    gmm.save_model('model_voip/vad_%s_sds_mfcc.gmm' % name)
    return


if __name__ == '__main__':

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

    vta = MLFMFCCOnlineAlignedArray(usec0=False)
    # vta.append_mlf(mlf_sil)
    # vta.append_trn(train_data_sil)
    vta.append_mlf(mlf_speech)
    vta.append_trn(train_data_speech)

    print "Generating the MFCC features"
    train = []
    test = []
    i = 0
    for frame, label in vta:
        if i % (n_max_frames / 10) == 0:
            print "Already processed: %.2f%% of data" % (100.0*i/n_max_frames)

        if i > n_max_frames:
            break


        if i < n_crossvalid_frames:
            test.append((frame, label))
        else:
            train.append((frame, label))

        i += 1

    p_speech = Process(target=train_gmm, args=('speech',train))
    p_sil = Process(target=train_gmm, args=('sil', train))
    p_speech.start()
    p_sil.start()

    p_sil.join()
    print "Sil GMM training finished"
    print datetime.datetime.now()
    p_speech.join()
    print "Speech GMM training finished"
    print datetime.datetime.now()

    #train_speech_gmm()
    #train_sil_gmm()


    print '-' * 120
    print 'VAD GMM test'
    print datetime.datetime.now()
    print '-' * 120
    gmm_speech = GMM(n_features=0)
    gmm_speech.load_model('model_voip/vad_speech_sds_mfcc.gmm')
    gmm_sil = GMM(n_features=0)
    gmm_sil.load_model('model_voip/vad_sil_sds_mfcc.gmm')


    vta = test

    print "Length of test data:", len(vta)
    print datetime.datetime.now()

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

    accuracy = accuracy * 100.0 / n

    print "VAD accuracy : %0.3f%% " % accuracy
    print datetime.datetime.now()
