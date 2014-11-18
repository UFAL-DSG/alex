#!/usr/bin/env python
# -*- coding: utf-8 -*-

from alex.utils.config import online_update

if __name__ == '__main__':
    import autopath

    online_update("applications/PublicTransportInfoCS/slu/dainnclassifier/dainn.nbl.model.all")
