#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from alex.applications.PublicTransportInfoCS.slu.test import trained_slu_test, hdc_slu_test
from alex.components.asr.utterance import Utterance


if __name__ == '__main__':
    import autopath
    hdc_slu_test('./bootstrap.trn', Utterance, './bootstrap.sem')
