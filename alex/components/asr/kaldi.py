#!/usr/bin/env python
# -*- coding: utf-8 -*-

# author: Ondrej Platek
from alex.components.asr.utterance import UtteranceNBList, Utterance
from alex.components.asr.exceptions import KaldiSetupException
from pykaldi.utils import wst2dict, lattice_to_nbest
try:
    from pykaldi.decoders import PyGmmLatgenWrapper
except ImportError as e:
    # FIXME PYTHONPATH I can change : sys.path insert into(0,)
    raise KaldiSetupException('%s\nTry setting PYTHONPATH or LD_LIBRARY_PATH' % e.message)
import time


class KaldiASR(object):

    """ Wraps Kaldi lattice decoder,

    which firstly decodes in forward direction and generate on demand lattice
    by traversing pruned decoding graph backwards.
    """

    def __init__(self, cfg):
        self.logger = cfg['Logging']['system_logger']
        self.cfg = cfg
        kcfg = cfg['ASR']['Kaldi']
        self.wst = wst2dict(kcfg['wst'])
        self.max_dec_frames = kcfg['max_dec_frames']
        # specify all other options in config
        argv = ("--config=%(config)s --verbose=%(verbose)d "
                "%(model)s %(hclg)s %(silent_phones)s" % kcfg)
        argv = argv.split()
        with open(kcfg['config']) as r:
            conf_opt = r.read()
            self.logger.info('argv: %s\nconfig: %s' % (argv, conf_opt))

        self.decoder = PyGmmLatgenWrapper()
        self.decoder.setup(argv)
        self.decoder.reset(keep_buffer_data=False)  # FIXME is it necessary?

    def flush(self):
        """
        Should reset Kaldi in order to be ready for next recognition task
        :returns: self - The instance of KaldiASR
        """
        self.decoder.reset(keep_buffer_data=False)
        return self

    def rec_in(self, frame):
        """This defines asynchronous interface for speech recognition.

        Call this input function with audio data belonging into one speech segment
        that should be recognized.

        :frame: @todo
        :returns: self - The instance of KaldiASR
        """
        start = time.clock()
        self.decoder.frame_in(frame.payload)
        self.logger.info('frame_in of %d frames' % (len(frame.payload) / 2))
        dec_t = self.decoder.decode(max_frames=self.max_dec_frames)
        while dec_t > 0:
            dec_t = self.decoder.decode(max_frames=self.max_dec_frames)
        self.logger.info('Forward decoding of %d frames in %s secs' % (
            dec_t, str(time.clock() - start)))
        return self

    def hyp_out(self):
        """ This defines asynchronous interface for speech recognition.
        Returns recognizers hypotheses about the input speech audio.
        """
        start = time.clock()
        self.decoder.prune_final()
        lat = self.decoder.get_lattice()
        nbest = lattice_to_nbest(lat, n=5)
        nblist = UtteranceNBList()
        for w, word_ids in nbest:
            words = [self.wst[str(i)] for i in word_ids]
            nblist.add(w, Utterance(words))
        self.logger.info('hyp_out: get_lattice+nbest in %s secs' % str(time.clock() - start))
        if len(nbest) == 0:
            self.logger.warning('hyp_out: empty hypothesis')
            nblist.add(1.0, Utterance('Empty hypothesis: DEBUG'))

        return nblist
