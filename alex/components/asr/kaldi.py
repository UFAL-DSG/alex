#!/usr/bin/env python
# -*- coding: utf-8 -*-

# author: Ondrej Platek
from alex.components.asr.utterance import UtteranceNBList, UtteranceConfusionNetwork, Utterance
from alex.components.asr.kaldiException import KaldiSetupException
import os
import os.path
import sys


'''
Remarks
I can generate following classes in which can be accepted by SLU
described in ASR alex/components/slu/base.py:564

    def parse(self, utterance, *args, **kw):
        """Check what the input is and parse accordingly."""

        if isinstance(utterance, Utterance):
            return self.parse_1_best(utterance, *args, **kw)

        elif isinstance(utterance, UtteranceHyp):
            return self.parse_1_best(utterance, *args, **kw)

        elif isinstance(utterance, UtteranceNBList):
            return self.parse_nblist(utterance, *args, **kw)

        elif isinstance(utterance, UtteranceConfusionNetwork):
            return self.parse_confnet(utterance, *args, **kw)

        else:
            raise DAILRException("Unsupported input in the SLU component.")
'''


class KaldiASR(object):
    '''
    Just now it is empty stub with public interface
    '''
    # do not set up env. variables twice
    _set_path_executed = False

    def __init__(self, cfg):
        self.logger = cfg['Logging']['system_logger']
        self.cfg = cfg
        Kcfg = cfg['ASR']['Kaldi']
        self.debug = cfg['ASR'].get('debug', False)

        hyp_type = Kcfg['hypothesis_type']
        if hyp_type == 'confnet':
            self._hyp_out = self._decode_confnet
        elif hyp_type == 'nblist':
            self.hyp_out = self._decode_nblist
        else:
            raise KaldiSetupException("Not supported output type")

        self._set_path(Kcfg['ENV_SETTINGS'])
        self.model = Kcfg['model']
        self.LM_scale = Kcfg['LM_scale']
        self.lat_depth = Kcfg['lat_depth']
        # etc: FIXME
        # self.max_active
        # self.beam
        # self.latbeam
        # self.acoustic_scale
        # self.wst
        # self.hclg
        self.logger.info('debug:%r\nmodel:%s\nLM_scale:%f\nlat_depth:%d\n' % (
            self.debug, self.model, self.LM_scale, self.lat_depth))

    def _set_path(self, d):
        """Set the environment (LD_LIBRARY_PATH, PYTHON_PATH)
        for running Kaldi.
        :d: Dictionary containing system and Python variables
        """
        if KaldiASR._set_path_executed:
            self.logger.debug('Setting ENVIROMENT VARIABLE SECOND time!')
        else:
            for k, path in d.iteritems():
                if not os.path.isdir(path):
                    raise KaldiSetupException(
                        'Cannot set %s.\n%s\nPath does not exists!\n' % (k, path))
            sys.path.append(d['kaldi_python'])
            llp = os.environ['LD_LIBRARY_PATH'].rstrip(':')
            os.environ['LD_LIBRARY_PATH'] = ':'.join([llp, d['openblas'], d['openfst'], d['portaudio']])
            self.logger.debug(os.environ['LD_LIBRARY_PATH'])

    def _decode_confnet(self, arg1):
        """@todo: Docstring for _decode_confnet

        :arg1: @todo
        :returns: Instance of UtteranceConfusionNetwork
        """
        cn = UtteranceConfusionNetwork()
        return cn

    def _decode_nblist(self):
        """@todo: Docstring for _decode_nblist
        :returns: instance of UtteranceNBList

        """
        nb = UtteranceNBList()

        # FIXME
        nb.add(1.0, Utterance('This is decoded UTTERANCE :) Testing purposes [Oplatek]!'))

        return nb

    def hyp_out(self):
        """ This defines asynchronous interface for speech recognition.
        It returns recognized hypothesis.

        :returns: Object of type Utterance|UtteranceHyp|etc. based on self.cfg
        """
        return self._hyp_out()

    def flush(self):
        """
        Should reset Kaldi in order to be ready for next recognition task
        :returns: self - The instance of KaldiASR
        """
        return self

    def rec_in(self, frame):
        """This defines asynchronous interface for speech recognition.

        Call this input function with audio data belonging into one speech segment that should be recognized.

        FIXME for now it just buffers the data.

        :frame: @todo
        :returns: self - The instance of KaldiASR
        """
        # self.rec_buffer.append(frame.payload)
        return self
