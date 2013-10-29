#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os.path
import codecs
import autopath

from alex.applications.PublicTransportInfoCS.slu.test import trained_slu_test, hdc_slu_test
from alex.components.asr.utterance import Utterance

hdc_slu_test('./bootstrap.trn', Utterance, './bootstrap.sem')

trained_slu_test('./dailogreg.trn.model', './bootstrap.trn', Utterance, './bootstrap.sem')
trained_slu_test('./dailogreg.asr.model', './bootstrap.trn', Utterance, './bootstrap.sem')
trained_slu_test('./dailogreg.nbl.model', './bootstrap.trn', Utterance, './bootstrap.sem')

