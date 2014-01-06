#!/usr/bin/env python
# encoding: utf-8

import autopath

from alex.utils.config import online_update


online_update('resources/asr/voip_cs/kaldi/HCLG.fst')
online_update('resources/asr/voip_cs/kaldi/final.mat')
online_update('resources/asr/voip_cs/kaldi/final.mdl')
online_update('resources/asr/voip_cs/kaldi/words.txt')
