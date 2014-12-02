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
    slu = PTICSHDCSLU(preprocessing, cfg = {'SLU': {PTICSHDCSLU: {'utt2da': as_project_path("applications/PublicTransportInfoCS/data/utt2da_dict.txt")}}})

    da = slu.parse_1_best({'utt':Utterance(utterance)}, verbose=True).get_best_da()

    print "Resulting dialogue act: \n", unicode(da)
