#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import numpy as np
import datetime
import lmj.cli
import theanets

from collections import deque

import autopath

from alex.utils.htk import *
from alex.ml import ffnn

lmj.cli.enable_default_logging()

""" This script trains NN for VAD.

"""

# the default values, these may be overwritten by teh script parameters

max_frames = 100000
max_files = 1000000
max_frames_per_segment = 50
trim_segments = 0
max_epoch = 3
hidden_units = 128
last_frames = 0
crossvalid_frames = int((0.20 * max_frames ))  # cca 20 % of all training data
usec0=0
preconditioner=0
hidden_dropouts=0
weight_l2=0

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

def train_nn(mlf_speech, train_data_speech):
    vta = MLFMFCCOnlineAlignedArray(usec0=usec0,n_last_frames=last_frames)
    # vta.append_mlf(mlf_sil)
    # vta.append_trn(train_data_sil)
    vta.append_mlf(mlf_speech)
    vta.append_trn(train_data_speech)

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

    print "Generating the cross-validation and train MFCC features"
    crossvalid_x = []
    crossvalid_y = []
    train_x = []
    train_y = []
    i = 0
    for frame, label in vta:
        if i % (max_frames / 10) == 0:
            print "Already processed: %.2f%% of data" % (100.0*i/max_frames)

        if i > max_frames:
            break

        if i < crossvalid_frames:
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

    epoch = 0
    while True:
        
        predictions_y = e.network.predict(crossvalid_x)
        c_acc, c_sil = get_accuracy(crossvalid_y, predictions_y)
        predictions_y = e.network.predict(train_x)
        t_acc, t_sil = get_accuracy(train_y, predictions_y)

        print
        print "max_frames, max_files, max_frames_per_segment, trim_segments, max_epoch, hidden_units, last_frames, crossvalid_frames, usec0, preconditioner, hidden_dropouts, weight_l2"
        print max_frames, max_files, max_frames_per_segment, trim_segments, max_epoch, hidden_units, last_frames, crossvalid_frames, usec0, preconditioner, hidden_dropouts, weight_l2
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
        nn.save(file_name = "model_voip/vad_sds_mfcc_is%d_hu%d_lf%d_mfr%d_mfl%d_mfps%d_ts%d_usec0%d.nn" % \
                            (input_size, hidden_units, last_frames, max_frames, max_files, max_frames_per_segment, trim_segments, usec0))


##################################################

def main():
    global max_frames, max_files, max_frames_per_segment, trim_segments, max_epoch, hidden_units, last_frames, crossvalid_frames, usec0
    global preconditioner, hidden_dropouts, weight_l2

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
    preconditioner = args.preconditioner
    hidden_dropouts = args.hidden_dropouts
    weight_l2 = args.weight_l2

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

    train_nn(mlf_speech, train_data_speech)


if __name__ == "__main__":
    main()
