#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import numpy
import re
import glob
import wave

from struct import unpack, pack

from alex.utils.cache import lru_cache
from alex.utils.mfcc import MFCCFrontEnd

"""
The htk module implements classes for manipulation with the MLF files.
"""

LPC = 1
LPCREFC = 2
LPCEPSTRA = 3
LPCDELCEP = 4
IREFC = 5
MFCC = 6
FBANK = 7
MELSPEC = 8
USER = 9
DISCRETE = 10
PLP = 11

_E = 0000100  # has energy
_N = 0000200  # absolute energy supressed
_D = 0000400  # has delta coefficients
_A = 0001000  # has acceleration (delta-delta) coefficients
_C = 0002000  # is compressed
_Z = 0004000  # has zero mean static coefficients
_K = 0010000  # has CRC checksum
_O = 0020000  # has 0th cepstral coefficient
_V = 0040000  # has VQ data
_T = 0100000  # has third differential coefficients


class Features:

    "Read HTK format feature files"

    def __init__(self, file_name=None):
        self.swap = (unpack('=i', pack('>i', 42))[0] != 42)

        self.frames = []

        self.file_name = file_name
        if self.file_name:
            self.open(file_name)

    def __len__(self):
        return len(self.frames)

    def __iter__(self):
        for i in self.frames:
            yield i

    def __getitem__(self, i):
        return self.frames[i]

    def open(self, file_name):
        # pylint: disable-msg=E1103

        f = open(file_name, "rb")

        # read header
        spam = f.read(12)
        self.nSamples, self.sampPeriod, self.sampSize, self.parmKind = unpack(
            ">IIHH", spam)

        # get coefficients for compressed data
        if self.parmKind & _C:
            self.dtype = 'h'
            self.veclen = self.sampSize / 2
            if self.parmKind & 0x3f == IREFC:
                self.A = 32767
                self.B = 0
            else:
                self.A = numpy.fromfile(f, 'f', self.veclen)
                self.B = numpy.fromfile(f, 'f', self.veclen)
                if self.swap:
                    self.A = self.A.byteswap()
                    self.B = self.B.byteswap()
        else:
            self.dtype = 'f'
            self.veclen = self.sampSize / 4

        self.hdrlen = f.tell()

        data = numpy.fromfile(f, self.dtype)
        if self.parmKind & _K:
            # remove and ignore check-sum
            data = data[:-1]

        data = data.reshape(len(data) / self.veclen, self.veclen)

        if self.swap:
            data = data.byteswap()

        # un-compress data to floats if required
        if self.parmKind & _C:
            data = (data.astype('f') + self.B) / self.A

        self.frames = data

        f.close()


class MLF:

    """Read HTK MLF files.

    Def: segment is a sequence of frames with the same label.
    """

    def __init__(self, file_name=None, max_files=None):
        self.mlf = {}
        self.max_files = max_files

        self.file_name = file_name
        if self.file_name:
            self.open(file_name)

    def __len__(self):
        return len(self.mlf)

    def __iter__(self):
        for i in self.mlf:
            yield i

    def __getitem__(self, i):
        return self.mlf[i]

    def open(self, file_name):
        f = open(file_name, 'r')

        n_files = 0
        for l in f:
            if self.max_files and n_files > self.max_files:
                break
            l = l.strip()

            if l.startswith('"'):
                param_file_name = l[1:-1].replace("*/", '')
                param_file_name = re.sub(r"\.rec$", "", param_file_name)
                param_file_name = re.sub(r"\.lab$", "", param_file_name)
                transcription = []
                continue

            if l.startswith('.'):
                self.mlf[param_file_name] = transcription
                n_files += 1
                continue

            c = l.split()

            if len(c) == 3:
                # I get aligned mlf
                s, e, label = c
                s, e = int(s), int(e)

                m = label.find('-')
                p = label.rfind('+')
                if m != -1 and p != -1:
                    label = label[m + 1:p]

                transcription.append([s, e, label])
            elif len(c) == 1:
                # non aligned data
                pass

        f.close()

    def filter_zero_segments(self):
        """Remove aligned segments which have zero length."""
        for f in self.mlf:
            transcription = []
            for s, e, l in self.mlf[f]:
                if s == e:
                    # skip
                    continue
                else:
                    transcription.append([s, e, l])

            self.mlf[f] = transcription

    def sub(self, pattern, repl, pos=True):
        for f in self.mlf:
            for i, [s, e, l] in enumerate(self.mlf[f]):
                if pos and l == pattern:
                    self.mlf[f][i][2] = repl
                if not pos and l != pattern:
                    self.mlf[f][i][2] = repl

    def merge(self):
        """Merge the consecutive segments with the same label into one segment."""
        for f in self.mlf:
            transcription = []
            prev_w = None
            prev_start = 0
            prev_end = 0

            # print f

            for s, e, l in self.mlf[f]:

                # print "O", s, e, l

                if l == prev_w:
                    # merge
                    prev_end = e
                else:
                    if prev_w:
                        transcription.append([prev_start, prev_end, prev_w])
                        # print "N", prev_start, prev_end, prev_w
                    prev_start, prev_end, prev_w = s, e, l

            if prev_w:
                transcription.append([prev_start, prev_end, prev_w])

                # print "N", prev_start, prev_end, prev_w

            self.mlf[f] = transcription

    def times_to_seconds(self):
        for f in self.mlf:
            for i in range(len(self.mlf[f])):
                self.mlf[f][i][0] /= 10000000
                self.mlf[f][i][1] /= 10000000

    def times_to_frames(self, frame_length=0.010):
        for f in self.mlf:
            for i in range(len(self.mlf[f])):
                self.mlf[f][i][0] = int(self.mlf[f][i][0] / frame_length / 10000000)
                self.mlf[f][i][1] = int(self.mlf[f][i][1] / frame_length / 10000000)

            # shorten the last segment by 10 frames as there may not be enough data for a final frame
            self.mlf[f][i][1] -= 10

            # remove the zero or negative length segments that could be created by the previous step
            if self.mlf[f][i][0] >= self.mlf[f][i][1]:
                del self.mlf[f][i]

    def trim_segments(self, n=3):
        """Remove n-frames from the beginning and the end of a segment."""
        if n:
            for f in self.mlf:
                transcription = []
                for s, e, l in self.mlf[f]:
                    if s + n < e - n:
                        # trim
                        transcription.append([s + n, e - n, l])
                    else:
                        # skip this segment as it is too short to be accuratelly aligned
                        pass

                self.mlf[f] = transcription

    def shorten_segments(self, n=100):
        """Shorten segments to n-frames."""
        if n:
            for f in self.mlf:
                # print f
                transcription = []
                for s, e, l in self.mlf[f]:
                    if e - s > 2*n+2:
                        # clip the middle part of the segment
                        transcription.append([s, s + n, l])
                        transcription.append([e-n-1, e-1, l])

                        # print transcription[-2]
                        # print transcription[-1]
                        # print '.'
                    else:
                        # it is short enough
                        transcription.append([s, e, l])

                        # print transcription[-1]
                        # print '.'

                self.mlf[f] = transcription

    def count_length(self, pattern):
        """Count length of all segments matching the pattern"""
        length = 0

        for f in self.mlf:
            for s, e, l in self.mlf[f]:
                if l == pattern:
                    length += e - s

        return length


class MLFFeaturesAlignedArray:

    """Creates array like object from multiple mlf files and corresponding audio data.
    For each aligned frame it returns a feature vector and its label.

    If a filter is set to a particular value, then only frames with the label equal to the filer will be returned.
    In this case, the label is not returned when iterating through the array.

    """

    def __init__(self, filter=None):
        self.filter = filter
        self.mlfs = []
        self.trns = []
        self.last_file_name = None
        self.last_param_file_features = None

    def __iter__(self):
        """Allows to iterate over all frames in the the appended mlf and param files.
        The required data are loaded as necessary. This is a memory efficient solution
        """
        for mlf in self.mlfs:
            for f in mlf:
                for s, e, l in mlf[f]:
                    for i in range(s, e):
                        # print f, s, e, l, i
                        if self.filter:
                            if l == self.filter:
                                yield self.get_frame(f, i)
                            else:
                                # skip a frame not matching the filter
                                continue
                        else:
                            yield [self.get_frame(f, i), l]

    def append_mlf(self, mlf):
        """Add a mlf file with aligned transcriptions."""
        self.mlfs.append(mlf)

    def append_trn(self, trn):
        """Adds files with audio data (param files) based on the provided pattern."""
        trn_files = glob.glob(trn)
#    print "TF", trn_files
        self.trns.extend(trn_files)

    @lru_cache(maxsize=100000)
    def get_param_file_name(self, file_name):
        """Returns the matching param file name."""
        for trn in self.trns:
            if file_name in trn:
                return trn

    def get_frame(self, file_name, frame_id):
        """Returns a frame from a specific param file."""
        if self.last_file_name != file_name:
            # find matching param file
            param_file_name = self.get_param_file_name(file_name)

            # open the param file
            self.last_param_file_features = Features(param_file_name)

            self.last_file_name = file_name

        return self.last_param_file_features[frame_id]


class MLFMFCCOnlineAlignedArray(MLFFeaturesAlignedArray):

    """This is an extension of MLFFeaturesAlignedArray which computes the features on the fly from
    the input wav files.

    It uses our own implementation of the MFCC computation. As a result it does not give the same results
    as the HTK HCopy.

    The experience suggests that our MFFC features are worse than the features generated by HCopy.

    """

    def __init__(self, windowsize=250000, targetrate=100000, filter=None,
                 usec0=False, usedelta=True, useacc=True,
                 n_last_frames=0, mel_banks_only = False):
        """Initialise the MFCC front-end.

        windowsize - defines the length of the window (frame) in the HTK's 100ns units
        targetrate - defines the period with which new coefficients should be generated (again in 100ns units)
        """
        MLFFeaturesAlignedArray.__init__(self, filter)

        self.windowsize = windowsize
        self.targetrate = targetrate
        self.usec0 = usec0
        self.usedelta = usedelta
        self.useacc = useacc
        self.n_last_frames = n_last_frames
        self.mel_banks_only = mel_banks_only

        self.mfcc_front_end = None

    def get_frame(self, file_name, frame_id):
        """Returns a frame from a specific param file."""
        if self.last_file_name != file_name:
            self.last_file_name = file_name

            # print "FN", file_name

            # find matching param file
            param_file_name = self.get_param_file_name(file_name)
            if param_file_name == None:
                raise Exception("MLFMFCCOnlineAlignedArray: param_file_name cannot be None, file_name: " + file_name)
            # print "PFN", param_file_name

            # open the param file
            try:
                self.last_param_file_features = wave.open(param_file_name, 'r')
            except AttributeError:
                print "Error opening file:", param_file_name

            if self.last_param_file_features.getnchannels() != 1:
                raise Exception('Input wave is not in mono')

            if self.last_param_file_features.getsampwidth() != 2:
                raise Exception('Input wave is not in 16bit')

            sample_rate = self.last_param_file_features.getframerate()
            self.frame_size = int(sample_rate * self.windowsize / 10000000)
            if self.frame_size > 1024:
                self.frame_size = 2048
            elif self.frame_size > 512:
                self.frame_size = 1024
            elif self.frame_size > 256:
                self.frame_size = 512
            elif self.frame_size > 128:
                self.frame_size = 256
            elif self.frame_size > 64:
                self.frame_size = 128

            self.frame_shift = int(sample_rate * self.targetrate / 10000000)
            self.mfcc_front_end = MFCCFrontEnd(sample_rate, self.frame_size, usec0=self.usec0,
                                               usedelta=self.usedelta, useacc=self.useacc,
                                               n_last_frames=self.n_last_frames, mel_banks_only = self.mel_banks_only)

        # print "FS", self.frame_size
        self.last_param_file_features.setpos(max(frame_id * self.frame_shift - int(self.frame_size / 2), 0))
        frame = self.last_param_file_features.readframes(self.frame_size)
        # print "LN", len(frame)

        frame = numpy.frombuffer(frame, dtype=numpy.int16)

        try:
            mfcc_params = self.mfcc_front_end.param(frame)
        except ValueError:
            print file_name, frame_id, len(frame)
            raise
            
        return mfcc_params
