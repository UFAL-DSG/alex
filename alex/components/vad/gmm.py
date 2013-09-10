#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import deque
import numpy as np
from scipy.misc import logsumexp
import struct

from alex.components.asr.exceptions import ASRException
from alex.ml.gmm import GMM
from alex.utils.mfcc import MFCCFrontEnd


class GMMVAD():
    """ This is implementation of a GMM based voice activity detector.

    It only implements decisions whether input frame is speech of non speech.
    It returns the posterior probability of speech for N last input frames.
    """
    def __init__(self, cfg):
        self.cfg = cfg

        self.audio_recorded_in = []

        self.gmm_speech = GMM()
        self.gmm_speech.load_model(self.cfg['VAD']['gmm']['speech_model'])
        self.gmm_sil = GMM()
        self.gmm_sil.load_model(self.cfg['VAD']['gmm']['sil_model'])

        self.log_probs_speech = deque(maxlen=self.cfg['VAD']['gmm']['filter_length'])
        self.log_probs_sil = deque(maxlen=self.cfg['VAD']['gmm']['filter_length'])

        self.last_decision = 0.0

        if self.cfg['VAD']['gmm']['frontend'] == 'MFCC':
            self.front_end = MFCCFrontEnd(
                self.cfg['Audio']['sample_rate'], self.cfg['VAD']['gmm']['framesize'],
                self.cfg['VAD']['gmm']['usehamming'], self.cfg['VAD']['gmm']['preemcoef'],
                self.cfg['VAD']['gmm']['numchans'], self.cfg['VAD']['gmm']['ceplifter'],
                self.cfg['VAD']['gmm']['numceps'], self.cfg['VAD']['gmm']['enormalise'],
                self.cfg['VAD']['gmm']['zmeansource'], self.cfg['VAD']['gmm']['usepower'],
                self.cfg['VAD']['gmm']['usec0'], self.cfg['VAD']['gmm']['usecmn'],
                self.cfg['VAD']['gmm']['usedelta'], self.cfg['VAD']['gmm']['useacc'],
                self.cfg['VAD']['gmm']['n_last_frames'],
                self.cfg['VAD']['gmm']['lofreq'], self.cfg['VAD']['gmm']['hifreq'])
        else:
            raise ASRException('Unsupported frontend: %s' % (self.cfg['VAD']['gmm']['frontend'], ))

    def decide(self, data):
        """Processes the input frame whether the input segment is speech or non speech.

        The returned values can be in range from 0.0 to 1.0.
        It returns 1.0 for 100% speech segment and 0.0 for 100% non speech segment.
        """

        data = struct.unpack('%dh' % (len(data) / 2, ), data)
        self.audio_recorded_in.extend(data)

        while len(self.audio_recorded_in) > self.cfg['VAD']['gmm']['framesize']:
            frame = self.audio_recorded_in[:self.cfg['VAD']['gmm']['framesize']]
            self.audio_recorded_in = self.audio_recorded_in[self.cfg['VAD']['gmm']['frameshift']:]

            mfcc = self.front_end.param(frame)

            log_prob_speech = self.gmm_speech.score(mfcc)
            log_prob_sil = self.gmm_sil.score(mfcc)

            self.log_probs_speech.append(log_prob_speech)
            self.log_probs_sil.append(log_prob_sil)

            log_prob_speech_avg = 0.0
            for log_prob_speech, log_prob_sil in zip(self.log_probs_speech, self.log_probs_sil):
                log_prob_speech_avg += log_prob_speech - logsumexp([log_prob_speech, log_prob_sil])
            log_prob_speech_avg /= len(self.log_probs_speech)

            prob_speech_avg = np.exp(log_prob_speech_avg)

#      print 'prob_speech_avg: %5.3f' % prob_speech_avg

            self.last_decision = prob_speech_avg

        # returns a speech / non-speech decisions
        return self.last_decision
