#!/usr/bin/env python
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import autopath
from alex.utils.config import online_update

if __name__ == '__main__':
    online_update('applications/PublicTransportInfoCS/hclg/models/mfcc.conf')
    online_update('applications/PublicTransportInfoCS/hclg/models/tri2b_bmmi.mdl')
    online_update('applications/PublicTransportInfoCS/hclg/models/tri2b_bmmi.mat')
    online_update('applications/PublicTransportInfoCS/hclg/models/HCLG_tri2b_bmmi.fst')
    online_update('applications/PublicTransportInfoCS/hclg/models/words.txt')
    online_update('applications/PublicTransportInfoCS/hclg/models/silence.csl')
