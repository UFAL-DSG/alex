#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import autopath

from alex.applications.PublicTransportInfoCS.slu.test import trained_slu_test, hdc_slu_test
from alex.components.asr.utterance import Utterance

def main():
    hdc_slu_test('./bootstrap.trn', Utterance, './bootstrap.sem')

if __name__ == '__main__':
    main()
