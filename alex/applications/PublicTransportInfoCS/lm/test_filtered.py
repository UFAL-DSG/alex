#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script test filtered language model.
"""
if __name__ == '__main__':
    import os
    import xml.dom.minidom
    import glob
    import codecs
    import random

    import autopath

    extended_data_text_trn_norm_cls_pg_arpa_filtered    = "25_extended_data_trn_norm_cls.filtered.pg.arpa"

###############################################################################################

    if os.path.exists(extended_data_text_trn_norm_cls_pg_arpa_filtered):
        print
        print "Testing filtered"
        print "-"*120
        ###############################################################################################


        with codecs.open(extended_data_text_trn_norm_cls_pg_arpa_filtered) as f:
            for l in f:
               l = l.strip()
               l = l.replace('_INHALE_', '')
               l = l.replace('_NOISE_', '')
               l = l.replace('_EHM_HMM_', '')
               l = l.replace('_LAUGH_', '')
               
               c = l.count('CL_')
               
               if c > 1:
                   print l
               
               
               