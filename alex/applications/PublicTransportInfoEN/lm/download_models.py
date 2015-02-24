#!/usr/bin/env python
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import autopath

from alex.utils.config import online_update

if __name__ == '__main__':
    online_update('applications/PublicTransportInfoEN/lm/final.bg.arpa')
    online_update('applications/PublicTransportInfoEN/lm/final.tg.arpa')
    online_update('applications/PublicTransportInfoEN/lm/final.qg.arpa')
    online_update('applications/PublicTransportInfoEN/lm/final.pg.arpa')
    online_update('applications/PublicTransportInfoEN/lm/final.dict')
    online_update('applications/PublicTransportInfoEN/lm/final.dict.sp_sil')
    online_update('applications/PublicTransportInfoEN/lm/final.vocab')
