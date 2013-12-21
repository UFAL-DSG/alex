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
from datetime import datetime
import os


class KaldiASR(object):

    """ Wraps Kaldi lattice decoder,

    which firstly decodes in forward direction and generate on demand lattice
    by traversing pruned decoding graph backwards.
    """

    def __init__(self, cfg):
        self.logger = cfg['Logging']['system_logger']
        self.cfg = cfg
        kcfg = cfg['ASR']['Kaldi']

        self.debug = kcfg['debug']
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
        frame_total, start = 0, time.clock()
        self.decoder.frame_in(frame.payload)
        self.logger.debug('frame_in of %d frames' % (len(frame.payload) / 2))
        dec_t = self.decoder.decode(max_frames=self.max_dec_frames)
        while dec_t > 0:
            frame_total += dec_t
            dec_t = self.decoder.decode(max_frames=self.max_dec_frames)
        if (frame_total > 0):
            self.logger.debug('Forward decoding of %d frames in %s secs' % (
                frame_total, str(time.clock() - start)))
        return self

    def hyp_out(self):
        """ This defines asynchronous interface for speech recognition.
        Returns recognizers hypotheses about the input speech audio.
        """
        start = time.clock()

        # Get hypothesis
        self.decoder.prune_final()
        utt_prob, lat = self.decoder.get_lattice()
        self.decoder.reset(keep_buffer_data=False)

        # Convert lattice to nblist
        nbest = lattice_to_nbest(lat, n=5)
        nblist = UtteranceNBList()
        for w, word_ids in nbest:
            words = ' '.join([self.wst[str(i)] for i in word_ids])
            nblist.add(w, Utterance(words))

        # Log
        if len(nbest) == 0:
            self.logger.warning('hyp_out: empty hypothesis')
            nblist.add(1.0, Utterance('Empty hypothesis: DEBUG'))
        if self.debug:
            output_file_name = os.path.join(
                self.logger.get_session_dir_name(),
                '%s.fst' % str(datetime.now().strftime('%Y-%m-%d-%H-%M-%S.%f')))
            lat.write(output_file_name)
        self.logger.info('utterance "probability" is %f' % utt_prob)
        self.logger.debug('hyp_out: get_lattice+nbest in %s secs' % str(time.clock() - start))

        return nblist
