#!/usr/bin/env python
# -*- coding: utf-8 -*-

# author: Ondrej Platek
from alex.components.asr.utterance import UtteranceNBList, UtteranceConfusionNetwork, Utterance
from alex.components.asr.kaldiException import KaldiSetupException
try:
    from kaldi_decoders import NbListDecoder, ConfNetDecoder
except ImportError as e:
    raise KaldiSetupException('%s\nTry setting PYTHONPATH' % e.message)


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

        self.setDecoderType(Kcfg['hypothesis_type'])

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

    def setDecoderType(self, hyp_type):
        if hyp_type == 'confnet':
            self.decoder = ConfNetDecoder()
            self.hyp_out = self._decode_confnet
        elif hyp_type == 'nblist':
            self.decoder = NbListDecoder()
            self.hyp_out = self._decode_nblist
        else:
            raise KaldiSetupException("Not supported output type")

    def _decode_confnet(self):
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
        dnb = self.decoder.decode()
        nb = UtteranceNBList()
        for prob, hyp in dnb:
            nb.add(prob, Utterance(hyp))
        return nb

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
