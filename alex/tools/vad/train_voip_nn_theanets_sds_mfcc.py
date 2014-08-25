#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import numpy as np
import datetime
import random
import lmj.cli
import theanets

from collections import deque

import autopath

from alex.utils.htk import *
from alex.ml import ffnn

lmj.cli.enable_default_logging()

""" This script trains NN for VAD.

"""

#random.seed(1)
# the default values, these may be overwritten by the script parameters

max_frames = 10000
max_files = 1000000
max_frames_per_segment = 50
trim_segments = 0
max_epoch = 3
hidden_units = 32
last_frames = 3
crossvalid_frames = int((0.20 * max_frames ))  # cca 20 % of all training data
usec0=0
usedelta=False
useacc=False
mel_banks_only=1 # True
preconditioner=0
hidden_dropouts=0
weight_l2=0

def load_mlf(train_data_sil_aligned, max_files, max_frames_per_segment):
    """ Loads a MLF file and creates normalised MLF class.

    :param train_data_sil_aligned:
    :param max_files:
    :param max_frames_per_segment:
    :return:
    """
    mlf = MLF(train_data_sil_aligned, max_files=max_files)
    mlf.filter_zero_segments()
    # map all sp, _noise_, _laugh_, _inhale_ to sil
    mlf.sub('sp', 'sil')
    mlf.sub('_noise_', 'sil')
    mlf.sub('_laugh_', 'sil')
    mlf.sub('_inhale_', 'sil')
    # map everything except of sil to speech
    mlf.sub('sil', 'speech', False)
    mlf.merge()
    #mlf_sil.times_to_seconds()
    mlf.times_to_frames()
    mlf.trim_segments(trim_segments)
    mlf.shorten_segments(max_frames_per_segment)

    return mlf


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

def train_nn(speech_data, speech_alignment):
    vta = MLFMFCCOnlineAlignedArray(usec0=usec0,n_last_frames=last_frames, usedelta = usedelta, useacc = useacc, mel_banks_only = mel_banks_only)
    sil_count = 0
    speech_count = 0
    for sd, sa in zip(speech_data, speech_alignment):
        mlf_speech = load_mlf(sa, max_files, max_frames_per_segment)
        vta.append_mlf(mlf_speech)
        vta.append_trn(sd)

        sil_count += mlf_speech.count_length('sil')
        speech_count += mlf_speech.count_length('speech')

    print "The length of sil segments:    ", sil_count
    print "The length of speech segments: ", speech_count

    mfcc = vta.__iter__().next()

    print "MFCC length:", len(mfcc[0])
    input_size = len(mfcc[0])

    e = theanets.Experiment(theanets.Classifier,
                            layers=(input_size, hidden_units, hidden_units, hidden_units, hidden_units, 2),
                            optimize="hf",
                            num_updates=30,
                            validate=1,
                            initial_lambda=0.1,
                            preconditioner=True if preconditioner else False,
                            hidden_dropouts=hidden_dropouts,
                            weight_l2=weight_l2,
                            batch_size=500,
                            )

    random.seed(0)
    print "Generating the cross-validation and train MFCC features"
    crossvalid_x = []
    crossvalid_y = []
    train_x = []
    train_y = []
    i = 0
    for frame, label in vta:
        frame = frame - (10.0 if mel_banks_only else 0.0)
        
        if i % (max_frames / 10) == 0:
            print "Already processed: %.2f%% of data" % (100.0*i/max_frames)

        if i > max_frames:
            break

        if random.random() < float(crossvalid_frames)/max_frames:
            # sample validation (test) data
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

    print
    print "The length of training data: ", len(train_x)
    print "The length of test data:     ", len(crossvalid_x)
    print

    dc_acc = deque(maxlen=20)
    dt_acc = deque(maxlen=20)

    epoch = 0
    while True:
        
        predictions_y = e.network.predict(crossvalid_x)
        c_acc, c_sil = get_accuracy(crossvalid_y, predictions_y)
        predictions_y = e.network.predict(train_x)
        t_acc, t_sil = get_accuracy(train_y, predictions_y)

        print
        print "max_frames, max_files, max_frames_per_segment, trim_segments, max_epoch, hidden_units, last_frames, crossvalid_frames, usec0, usedelta, useacc, mel_banks_only, preconditioner, hidden_dropouts, weight_l2"
        print max_frames, max_files, max_frames_per_segment, trim_segments, max_epoch, hidden_units, last_frames, crossvalid_frames, usec0, usedelta, useacc, mel_banks_only, preconditioner, hidden_dropouts, weight_l2
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

        if epoch == max_epoch:
            break
        epoch += 1
            
        e.run(train, crossvalid)

        dc_acc.append(c_acc)
        dt_acc.append(t_acc)

        nn = ffnn.FFNN()
        for w, b in zip(e.network.weights, e.network.biases):
             nn.add_layer(w.get_value(), b.get_value())
        nn.save(file_name = "model_voip/vad_sds_mfcc_is%d_hu%d_lf%d_mfr%d_mfl%d_mfps%d_ts%d_usec0%d_usedelta%d_useacc%d_mbo%d.nn" % \
                            (input_size, hidden_units, last_frames, max_frames, max_files, max_frames_per_segment, trim_segments, usec0, usedelta, useacc, mel_banks_only))


##################################################

def main():
    global max_frames, max_files, max_frames_per_segment, trim_segments, max_epoch, hidden_units, last_frames, crossvalid_frames, usec0
    global preconditioner, hidden_dropouts, weight_l2
    global mel_banks_only

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""This program trains neural network VAD models using the theanets library.
      """)

    parser.add_argument('--max_frames', action="store", default=max_frames, type=int,
                        help='a number of frames used in training including the frames for the cross validation: default %d' % max_frames)
    parser.add_argument('--max_files', action="store", default=max_files, type=int,
                        help='a number of files from the MLF files used in training: default %d' % max_files)
    parser.add_argument('--max_frames_per_segment', action="store", default=max_frames_per_segment, type=int,
                        help='a maximum number of frames per segment (segment is a sequence of frames with the same label): default %d' % max_frames_per_segment)
    parser.add_argument('--trim_segments', action="store", default=trim_segments, type=int,
                        help='number of frames that are trimmed for beginning and the end of each segment: default %d' % trim_segments)
    parser.add_argument('--max_epoch', action="store", default=max_epoch, type=int,
                        help='number of training epochs: default %d' % max_epoch)
    parser.add_argument('--hidden_units', action="store", default=hidden_units, type=int,
                        help='number of hidden units: default %d' % hidden_units)
    parser.add_argument('--last_frames', action="store", default=last_frames, type=int,
                        help='number of last frames: default %d' % last_frames)
    parser.add_argument('--usec0', action="store", default=usec0, type=int,
                        help='use c0 in mfcc: default %d' % usec0)
    parser.add_argument('--mel_banks_only', action="store", default=mel_banks_only, type=int,
                        help='use mel banks only instead of mfcc: default %d' % mel_banks_only)
    parser.add_argument('--preconditioner', action="store", default=preconditioner, type=int,
                        help='use preconditioner for HF optimization: default %d' % preconditioner)
    parser.add_argument('--hidden_dropouts', action="store", default=hidden_dropouts, type=float,
                        help='proportion of hidden_dropouts: default %d' % hidden_dropouts)
    parser.add_argument('--weight_l2', action="store", default=weight_l2, type=float,
                        help='use weight L2 regularisation: default %d' % weight_l2)

    args = parser.parse_args()
    sys.argv = []

    max_frames = args.max_frames
    max_files = args.max_files
    max_frames_per_segment = args.max_frames_per_segment
    trim_segments = args.trim_segments
    max_epoch = args.max_epoch
    hidden_units = args.hidden_units
    last_frames = args.last_frames
    crossvalid_frames = int((0.20 * max_frames ))  # cca 20 % of all training data
    usec0 = args.usec0
    mel_banks_only = args.mel_banks_only
    preconditioner = args.preconditioner
    hidden_dropouts = args.hidden_dropouts
    weight_l2 = args.weight_l2


    # add all the training data
    train_speech = []
    train_speech_alignment = []

    train_speech.append('data_voip_en/train/*.wav')
    train_speech_alignment.append('model_voip_en/aligned_best.mlf')

    train_speech.append('data_voip_cs/train/*.wav')
    train_speech_alignment.append('model_voip_cs/aligned_best.mlf')


    print datetime.datetime.now()

    train_nn(train_speech, train_speech_alignment)


if __name__ == "__main__":
    main()
