#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Serves to quickly test HDC SLU with a single utterance supplied as argument
"""

if __name__ == '__main__':
    import autopath
import sys

from alex.utils.config import as_project_path

from alex.applications.PublicTransportInfoCS.hdc_slu import PTICSHDCSLU

from alex.applications.PublicTransportInfoCS.preprocessing import PTICSSLUPreprocessing
from alex.components.asr.utterance import Utterance
from alex.components.slu.base import CategoryLabelDatabase


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "No utterance entered as argument. Processing sample utterance instead..."
        utterance = u"CHTĚL BYCH JET ZE ZASTÁVKY ANDĚL DO ZASTÁVKY MALOSTRANSKÉ NÁMĚSTÍ"
    else:
        utterance = sys.argv[1].decode('utf-8')
        sys.argv = sys.argv[:1]

    cldb = CategoryLabelDatabase('../data/database.py')
    preprocessing = PTICSSLUPreprocessing(cldb)
    slu = PTICSHDCSLU(preprocessing, cfg={'SLU': {PTICSHDCSLU: {'utt2da': as_project_path("applications/PublicTransportInfoCS/data/utt2da_dict.txt")}}})

    norm_utterance = slu.preprocessing.normalise_utterance(Utterance(utterance))
    abutterance, _, _ = slu.abstract_utterance(norm_utterance)
    da = slu.parse_1_best({'utt': Utterance(utterance)}, verbose=True).get_best_da()
    print "Abstracted utterance:", unicode(abutterance)
    print "Dialogue act:", unicode(da)

    max_alignment_idx = lambda _dai: max(_dai.alignment) if _dai.alignment else len(abutterance)
    for i, dai in enumerate(sorted(da, key=max_alignment_idx)):
        if not dai.alignment:
            print "Empty alignment:", unicode(abutterance), ";", dai

        if not dai.alignment or dai.alignment == -1:
            dai_alignment_idx = len(abutterance)
        else:
            dai_alignment_idx = max(dai.alignment) + i + 1

        abutterance.insert(dai_alignment_idx, "[{} - {}]".format(dai, dai.alignment))
    print "Alignment:", unicode(abutterance)
