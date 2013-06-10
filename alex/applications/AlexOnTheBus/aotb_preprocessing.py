#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

from __future__ import unicode_literals

import autopath

from alex.components.slu.base import SLUPreprocessing
from alex.components.asr.utterance import Utterance
from alex.utils.czech_stemmer import cz_stem


class AOTBSLUPreprocessing(SLUPreprocessing):
    """\
    Extends SLUPreprocessing for some transformations specific for Czech:
        - devocalisation of prepositions
        - stemming.

    """
    def __init__(self, *args, **kwargs):
        super(AOTBSLUPreprocessing, self).__init__(*args, **kwargs)
        # XXX This is not very nice.  The parent class cares mainly about
        # normalising English, not Czech.
        self.text_normalization_mapping += [
            (['ve'], ['v']),
            (['ke'], ['k']),
            (['ku'], ['k']),
            (['ze'], ['z']),
            (['se'], ['s']),
        ]

    def text_normalisation(self, utterance):
        utterance = super(AOTBSLUPreprocessing,
                          self).text_normalisation(utterance)
        return Utterance(" ".join(map(cz_stem, utterance)))
