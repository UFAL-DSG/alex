#!/usr/bin/env python
# -*- coding: utf-8 -*-
import autopath

from alex.utils.config import online_update

online_update('applications/PublicTransportInfoCS/hclg/models/INFO_HCLG.txt')

online_update('applications/PublicTransportInfoCS/hclg/models/HCLG_tri2a.fst')
online_update('applications/PublicTransportInfoCS/hclg/models/tri2a.mdl')
online_update('applications/PublicTransportInfoCS/hclg/models/words.txt')
online_update('applications/PublicTransportInfoCS/hclg/models/silence.csl')
