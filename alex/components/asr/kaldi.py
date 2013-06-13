#!/usr/bin/env python
# -*- coding: utf-8 -*-

# author: Ondrej Platek
from alex.components.asr.exception import ASRException
from alex.components.asr.utterance import UtteranceNBList, UtteranceConfusionNetwork, Utterance


class KaldiException(ASRException):
    pass

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
    def __init__(self, cfg):
        self.cfg = cfg
        Kcfg = cfg['ASR']['Kaldi']

        self.debug = Kcfg.get('debug', False)

        hyp_type = Kcfg['hypothesis_type']
        if hyp_type == 'confnet':
            self._hyp_out = self._decode_confnet
        elif hyp_type == 'nblist':
            self.hyp_out = self._decode_nblist
        else:
            raise KaldiException("Not supported output type")

        self.model = Kcfg['model']
        self.LM_scale = Kcfg['LM_scale']
        self.lat_depth = Kcfg['lat_depth']
        # etc:
        # self.max_active
        # self.beam
        # self.latbeam
        # self.acoustic_scale
        # self.wst
        # self.hclg

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
        nb.add(1.0, Utterance('This is decoded UTTERANCE :) Testing purposes [Oplatek] --'))

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
        self.rec_buffer.append(frame.payload)
        return self
