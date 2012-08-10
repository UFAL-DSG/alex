#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from scipy.fftpack import dct
from collections import deque

class MFCCFrontEnd:
  """This is an a CLOSE approximation of MFCC coefficients computed by the HTK.

  It was not tested to give exactly the same results the HTK. As a result,
  it should not be used in conjunction with models trained on speech
  parametrised with the HTK.
  """

  def __init__(self, sourcerate = 16000, framesize = 400,
               usehamming = True, preemcoef = 0.97,
               numchans = 26, ceplifter = 22, numceps = 12,
               enormalize = True, zmeansource = True, usepower = True, usec0 = True, usecmn = True,
               usedelta = True,  useacc= True,
               lofreq = 125, hifreq = 3800):
    self.sourcerate = sourcerate
    self.framesize = framesize
    self.usehamming = usehamming
    self.preemcoef = preemcoef
    self.numchans = numchans
    self.ceplifter = ceplifter
    self.enormalize = enormalize
    self.zmeansource = zmeansource
    self.usepower = usepower
    self.usec0 = usec0
    self.usecmn = usecmn
    self.usedelta = usedelta
    self.useacc = useacc
    self.numceps = numceps
    self.lofreq = lofreq
    self.hifreq = hifreq

    self.prior = 0.0
    self.total_coefs = (numceps + int(usec0))*(1 + int(usedelta) + int(useacc))
    self.cmn = np.zeros(( self.total_coefs, ))
    self.cmn_alpha = 0.99
    self.mfcc_queue = deque(maxlen=3)
    self.mfcc_delta_queue = deque(maxlen=3)

    self.init_hamming()
    self.init_mel_filter_bank()
    self.init_cep_liftering_weights()

  def freq_to_mel(self, freq):
    return 1127 * np.log(1 + freq / 700.0)

  def mel_to_freq(self, mel):
    return 700 * (np.exp(freq / 1127 - 1))

  def init_hamming(self):
    self.hamming = np.hamming(self.framesize)

  def init_mel_filter_bank(self):
    """Initialise the triangular mel freq filters."""

    minMel = int(self.freq_to_mel(self.lofreq))
    maxMel = int(self.freq_to_mel(self.hifreq))

    # Create a matrix for triangular filters, one row per filter
    filterMatrix = np.zeros((self.numchans, self.framesize))

    melRange = np.array(xrange(self.numchans + 2))

    melCenterFilters = melRange * (maxMel - minMel) / (self.numchans + 1) + minMel

    # each array index represent the center of each triangular filter
    aux = np.log(1 + 1000.0 / 700.0) / 1000.0
    aux = (np.exp(melCenterFilters * aux) - 1) / 22050
    aux = 0.5 + 700 * self.framesize * aux
    aux = np.floor(aux)
    centerIndex = np.array(aux, int)  # Get int values

    for i in xrange(self.numchans):
      start, centre, end = centerIndex[i:i + 3]
      k1 = np.float32(centre - start)
      k2 = np.float32(end - centre)
      up = (np.array(xrange(start, centre)) - start) / k1
      down = (end - np.array(xrange(centre, end))) / k2

      filterMatrix[i][start:centre] = up
      filterMatrix[i][centre:end] = down

    self.mel_filter_bank = filterMatrix.transpose()

  def init_cep_liftering_weights(self):
    cep_lift_weights = np.zeros((self.numceps, ))
    a = np.pi/self.ceplifter
    b = self.ceplifter/2.0
    for i in range(self.numceps):
      cep_lift_weights[i] = 1.0 + b*np.sin(i*a)

    self.cep_lift_weights = cep_lift_weights

  def preemphasis(self, frame):
    out_frame = np.zeros_like(frame)
    out_frame[0] = frame[0] - self.preemcoef*self.prior
    for i in range(1, len(frame)):
      out_frame[i] = frame[i] - self.preemcoef*frame[i-1]

    self.prior = frame[1]

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
      frame = self.hamming*frame

    complex_spectrum = np.fft.fft(frame)
    power_spectrum = abs(complex_spectrum) ** 2
    mel_spectrum = np.dot(power_spectrum, self.mel_filter_bank)
    # apply mel floor
    for i in range(len(mel_spectrum)):
      if mel_spectrum[i] < 1.0:
        mel_spectrum[i] = 1.0
    # compute power spectrum if required
    if self.usepower:
      mel_spectrum = np.log(mel_spectrum)

    cepstrum = dct(mel_spectrum, type=2, norm='ortho')
    c0 = cepstrum[0]
    htk_cepstrum = cepstrum[1:self.numceps+1]
    # cepstral liftering
    cep_lift_mfcc = self.cep_lift_weights*htk_cepstrum

    if self.usec0:
      mfcc = np.append(cep_lift_mfcc, c0)
    else:
      mfcc = cep_lift_mfcc

    # compute delta and acceleration coefficients if requested
    self.mfcc_queue.append(mfcc)
    if self.usedelta:
#      print "LMQ", len(self.mfcc_queue)
      if len(self.mfcc_queue) > 2:
        delta = np.zeros_like(mfcc)
        for i in range(1, len(self.mfcc_queue)):
          delta += self.mfcc_queue[i] - self.mfcc_queue[i-1]
        delta /= len(self.mfcc_queue)

        self.mfcc_delta_queue.append(delta)
      else:
        delta = np.zeros_like(mfcc)

    if self.useacc:
      if len(self.mfcc_delta_queue) > 2:
        acc = np.zeros_like(mfcc)
        for i in range(1, len(self.mfcc_delta_queue)):
          acc += self.mfcc_delta_queue[i] - self.mfcc_delta_queue[i-1]
        acc /= len(self.mfcc_delta_queue)
      else:
        acc = np.zeros_like(mfcc)

    if self.usedelta:
      mfcc = np.append(mfcc, delta)
    if self.useacc:
      mfcc = np.append(mfcc, acc)

#    print cepstrum
#    print c0
#    print cep_lift_mfcc
#    print "MFCC", mfcc
#    print "LMFCC", len(mfcc)
#
    if self.usecmn:
      mfcc -= self.cmn
      self.cmn = self.cmn_alpha*self.cmn + (1.0-self.cmn_alpha)*mfcc

    return mfcc


