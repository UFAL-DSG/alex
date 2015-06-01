#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: Ondrej Platek
"""
Bringing Kaldi speech recogniser to alex ASRInterface
"""

from __future__ import unicode_literals

from math import exp
import time
import os

from alex.components.asr.base import ASRInterface
from alex.components.asr.utterance import UtteranceNBList, Utterance
from alex.components.asr.exceptions import KaldiSetupException
from alex.utils.lattice import lattice_to_word_posterior_lists, lattice_to_nbest, lattice_calibration

import kaldi.utils
try:
    from kaldi.decoders import PyOnlineLatgenRecogniser
except ImportError as e:
    raise KaldiSetupException('%s\nTry setting PYTHONPATH or LD_LIBRARY_PATH' % e.message)


class KaldiASR(ASRInterface):

    """ Wraps Kaldi PyOnlineLatgenRecogniser,

    which firstly decodes in forward direction and generate on demand lattice
    by traversing pruned decoding graph backwards.
    """

    def __init__(self, cfg):
        """
        Create KaldiASR instance and sets it according configuration

        Args:
            cfg(dict): Alex configuration
        """
        super(KaldiASR, self).__init__(cfg)
        kcfg = self.cfg['ASR']['Kaldi']
        if os.path.isfile(kcfg['silent_phones']):
            # replace the path of the file with its content
            with open(kcfg['silent_phones'], 'r') as r:
                kcfg['silent_phones'] = r.read()

        self.wst = kaldi.utils.wst2dict(kcfg['wst'])
        self.max_dec_frames = kcfg['max_dec_frames']
        self.n_best = kcfg['n_best']

        # specify all other options in config
        argv = ("--config=%(config)s --verbose=%(verbose)d %(extra_args)s "
                "%(model)s %(hclg)s %(silent_phones)s %(matrix)s" % kcfg)
        argv = argv.split()
        with open(kcfg['config']) as r:
            conf_opt = r.read()
            self.syslog.info('argv: %s\nconfig: %s' % (argv, conf_opt))

        self.calibration_table = kcfg['calibration_table'] if 'calibration_table' in kcfg else None

        self.last_lattice = None

        self.decoder = PyOnlineLatgenRecogniser()
        self.decoder.setup(argv)

    def flush(self):
        """
        Resets PyOnlineLatgenRecogniser in order to be ready for next recognition task

        Returns:
            self - The instance of KaldiASR
        """
        self.decoder.reset(reset_pipeline=True)
        return self

    def rec_in(self, frame):
        """Queueing in audio chunk

        Defines asynchronous interface for speech recognition.

        Args:
            frame(asr.components.hub.messages.Frame): store pcm payload
        Returns:
            self - The instance of KaldiASR
        """
        frame_total, start = 0, time.clock()
        self.decoder.frame_in(frame.payload)

        if self.cfg['ASR']['Kaldi']['debug']:
            self.syslog.debug('frame_in of %d frames' % (len(frame.payload) / 2))

        dec_t = self.decoder.decode(max_frames=self.max_dec_frames)
        while dec_t > 0:
            frame_total += dec_t
            dec_t = self.decoder.decode(max_frames=self.max_dec_frames)

        if self.cfg['ASR']['Kaldi']['debug']:
            if (frame_total > 0):
                self.syslog.debug('Forward decoding of %d frames in %s secs' % (
                    frame_total, str(time.clock() - start)))
        return self

    def hyp_out(self):
        """ This defines asynchronous interface for speech recognition.

        Returns:
            ASR hypothesis about the input speech audio.
        """
        start = time.time()

        # Get hypothesis
        self.decoder.finalize_decoding()
        utt_lik, lat = self.decoder.get_lattice()  # returns acceptor (py)fst.LogVectorFst
        self.decoder.reset(reset_pipeline=True)

        if self.calibration_table:
            lat = lattice_calibration(lat, self.calibration_table)

        self.last_lattice = lat

        # Convert lattice to nblist
        nbest = lattice_to_nbest(lat, self.n_best)
        nblist = UtteranceNBList()

        for w, word_ids in nbest:
            words = u' '.join([self.wst[i] for i in word_ids])

            if self.cfg['ASR']['Kaldi']['debug']:
                self.syslog.debug(words)

            p = exp(-w)
            nblist.add(p, Utterance(words))

        # Log
        if len(nbest) == 0:
            nblist.add(1.0, Utterance('Empty hypothesis: Kaldi __FAIL__'))

        nblist.merge()

        if self.cfg['ASR']['Kaldi']['debug']:
            self.syslog.info('utterance "likelihood" is %f' % utt_lik)
            self.syslog.debug('hyp_out: get_lattice+nbest in %s secs' % str(time.time() - start))

        return nblist

    def word_post_out(self):
        """ This defines asynchronous interface for speech recognition.

        Returns:
            ASR hypotheses.
        """

        # Get hypothesis
        self.decoder.finalize_decoding()
        utt_lik, lat = self.decoder.get_lattice()  # returns acceptor (py)fst.LogVectorFst
        self.last_lattice = lat

        self.decoder.reset(reset_pipeline=False)

        # Convert lattice to word nblist
        return lattice_to_word_posterior_lists(lat, self.n_best)

    def get_last_lattice(self):
        return self.last_lattice
