#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
if __name__ == '__main__':
    import autopath

from alex.applications.PublicTransportInfoCS.slu.dainnclassifier.test import trained_slu_test
from alex.components.asr.utterance import Utterance

if __name__ == '__main__':
    trained_slu_test('./dainn.trn.model.all', '../bootstrap.trn', Utterance, '../bootstrap.sem')
    trained_slu_test('./dainn.asr.model.all', '../bootstrap.trn', Utterance, '../bootstrap.sem')
    trained_slu_test('./dainn.nbl.model.all', '../bootstrap.trn', Utterance, '../bootstrap.sem')
