#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from scipy.fftpack import dct
from collections import deque


class MFCCKaldi:
    '''
    TODO port Kaldi mfcc to Python. Use similar parameters as
    in suggested in __init__ function
    '''

    def __init__(self, sourcerate=16000, framesize=512,
                 usehamming=True, preemcoef=0.97,
                 numchans=26, ceplifter=22, numceps=12,
                 enormalise=True, zmeansource=True, usepower=True, usec0=True,
                 usecmn=False, usedelta=True, useacc=True, n_last_frames=0,
                 lofreq=125, hifreq=3800, mel_banks_only=False):
        self.sourcerate = sourcerate
        self.framesize = framesize
        self.usehamming = usehamming
        self.preemcoef = preemcoef
        self.numchans = numchans
        self.ceplifter = ceplifter
        self.enormalise = enormalise
        self.zmeansource = zmeansource
        self.usepower = usepower
        self.usec0 = usec0
        self.usecmn = usecmn
        self.usedelta = usedelta
        self.useacc = useacc
        self.numceps = numceps
        self.lofreq = lofreq
        self.hifreq = hifreq
        self.mel_banks_only = mel_banks_only

    def param(self, frame):
        """Compute the MFCC coefficients in a way similar to the HTK."""


class MFCCFrontEnd:
    """This is an a CLOSE approximation of MFCC coefficients computed by the HTK.

    The frame size should be a number of power of 2.

    TODO: CMN is not implemented. It should normalise only teh cepstrum, not the delta or acc coefficients.

    It was not tested to give exactly the same results the HTK. As a result,
    it should not be used in conjunction with models trained on speech
    parametrised with the HTK.

    Over all it appears that this implementation of MFCC is worse than the one from the HTK.
    On the VAD task, the HTK features score 90.8% and the this features scores only 88.7%.
    """

    def __init__(self, sourcerate=16000, framesize=512,
                 usehamming=True, preemcoef=0.97,
                 numchans=26, ceplifter=22, numceps=12,
                 enormalise=True, zmeansource=True, usepower=True, usec0=True, usecmn=False,
                 usedelta=True, useacc=True, n_last_frames = 0,
                 lofreq=125, hifreq=3800, mel_banks_only = False):
        self.sourcerate = sourcerate
        self.framesize = framesize
        self.usehamming = usehamming
        self.preemcoef = preemcoef
        self.numchans = numchans
        self.ceplifter = ceplifter
        self.enormalise = enormalise
        self.zmeansource = zmeansource
        self.usepower = usepower
        self.usec0 = usec0
        self.usecmn = usecmn
        self.usedelta = usedelta
        self.useacc = useacc
        self.numceps = numceps
        self.lofreq = lofreq
        self.hifreq = hifreq
        self.mel_banks_only = mel_banks_only

        self.prior = 0.0

        self.n_last_frames = n_last_frames
        self.mfcc_queue = deque(maxlen=4 + n_last_frames)
        self.mfcc_delta_queue = deque(maxlen=4 + n_last_frames)

        self.init_hamming()
        self.init_mel_filter_bank()
        self.init_cep_liftering_weights()

    def freq_to_mel(self, freq):
        return 1127 * np.log(1.0 + freq / 700.0)

    def mel_to_freq(self, mel):
        return 700 * (np.exp(mel / 1127) - 1.0)

    def init_hamming(self):
        self.hamming = np.hamming(self.framesize)

    def init_mel_filter_bank(self):
        """Initialise the triangular mel freq filters."""

        minMel = self.freq_to_mel(self.lofreq)
        maxMel = self.freq_to_mel(self.hifreq)

#    print "MM", minMel, "MM", maxMel

        # Create a matrix for triangular filters, one row per filter
        filterMatrix = np.zeros((self.numchans, self.framesize / 2 + 1))

        melRange = np.array(xrange(self.numchans + 2))
#    print "MR", melRange

        melCenterFilters = melRange * (maxMel - minMel) / (
            self.numchans + 1) + minMel
#    print "MCF", melCenterFilters

        dfreq = self.sourcerate / self.framesize
        # each array index represent the center of each triangular filter
        centerIndex = np.array(
            np.round(self.mel_to_freq(melCenterFilters) / dfreq), int)
#    print "CI", centerIndex

        for i in xrange(self.numchans):
            start, centre, end = centerIndex[i:i + 3]
            k1 = np.float32(centre - start)
            k2 = np.float32(end - centre)
            up = (np.array(xrange(start, centre)) - start) / k1
            down = (end - np.array(xrange(centre, end))) / k2

            filterMatrix[i][start:centre] = up
            filterMatrix[i][centre:end] = down

        self.mel_filter_bank = filterMatrix.transpose()
#    print "SMFB", self.mel_filter_bank.shape

    def init_cep_liftering_weights(self):
        cep_lift_weights = np.zeros((self.numceps, ))
        a = np.pi / self.ceplifter
        b = self.ceplifter / 2.0
        for i in range(self.numceps):
            cep_lift_weights[i] = 1.0 + b * np.sin(i * a)

        self.cep_lift_weights = cep_lift_weights

    def preemphasis(self, frame):
        out_frame = np.zeros_like(frame)
        out_frame[0] = frame[0] - self.preemcoef * self.prior
        for i in range(1, len(frame)):
            out_frame[i] = frame[i] - self.preemcoef * frame[i - 1]

        self.prior = frame[-1]

        return out_frame

    def param(self, frame):
        """Compute the MFCC coefficients in a way similar to the HTK."""
        # zero mean
        if self.zmeansource:
            frame = frame - np.mean(frame)
        # preemphasis
        frame = self.preemphasis(frame)
        # apply hamming window
        if self.usehamming:
            frame = self.hamming * frame

        complex_spectrum = np.fft.rfft(frame)
#    print "LCS", len(complex_spectrum)
        power_spectrum = complex_spectrum.real * complex_spectrum.real + \
            complex_spectrum.imag * complex_spectrum.imag
        # compute only power spectrum if required
        if not self.usepower:
            power_spectrum = np.sqrt(power_spectrum)

#    print "SPS",power_spectrum.shape
        mel_spectrum = np.dot(power_spectrum, self.mel_filter_bank)
        # apply mel floor
        for i in range(len(mel_spectrum)):
            if mel_spectrum[i] < 1.0:
                mel_spectrum[i] = 1.0
        mel_spectrum = np.log(mel_spectrum)
        
        if self.mel_banks_only:
            mfcc = mel_spectrum
            self.mfcc_queue.append(mel_spectrum)
        else:
            cepstrum = dct(mel_spectrum, type=2, norm='ortho')
            c0 = cepstrum[0]
            htk_cepstrum = cepstrum[1:self.numceps + 1]
            # cepstral liftering
            cep_lift_mfcc = self.cep_lift_weights * htk_cepstrum

            if self.usec0:
                mfcc = np.append(cep_lift_mfcc, c0)
            else:
                mfcc = cep_lift_mfcc

            # compute delta and acceleration coefficients if requested
            self.mfcc_queue.append(mfcc)

#        print len(self.mfcc_queue)

            if self.usedelta:
#      print "LMQ", len(self.mfcc_queue)
                if len(self.mfcc_queue) >= 2:
                    delta = np.zeros_like(mfcc)
                    for i in range(1, len(self.mfcc_queue)):
                        delta += self.mfcc_queue[i] - self.mfcc_queue[i - 1]
                    delta /= len(self.mfcc_queue) - 1

                    self.mfcc_delta_queue.append(delta)
                else:
                    delta = np.zeros_like(mfcc)

            if self.useacc:
                if len(self.mfcc_delta_queue) >= 2:
                    acc = np.zeros_like(mfcc)
                    for i in range(1, len(self.mfcc_delta_queue)):
                        acc += self.mfcc_delta_queue[i] - \
                            self.mfcc_delta_queue[i - 1]
                    acc /= len(self.mfcc_delta_queue) - 1
                else:
                    acc = np.zeros_like(mfcc)

            if self.usedelta:
                mfcc = np.append(mfcc, delta)
            if self.useacc:
                mfcc = np.append(mfcc, acc)

        for i in range(self.n_last_frames):
            if len(self.mfcc_queue) > i + 1 :
                mfcc = np.append(mfcc, self.mfcc_queue[-1-i-1])
            else:
                mfcc = np.append(mfcc, np.zeros_like(self.mfcc_queue[-1]))

        return mfcc.astype(np.float32)
