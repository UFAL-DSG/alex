#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=E0602
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.

import sys
if __name__ == '__main__':
    import autopath
from alex.components.dm.ruledm.ruledm import RuleDM
from alex.components.dm.ruledm.pruledm import PRuleDM
from alex.components.dm.ruledm.druledmpolicy import DRuleDMPolicy

from alex.components.slu.da import DialogueActItem, DialogueActNBList
from alex.utils.caminfodb import CamInfoDb
from alex.utils.config import Config



class UfalRuleDMPolicy(DRuleDMPolicy):
    db_cls = CamInfoDb


class UfalRuleDM(RuleDM):
    policy_cls = UfalRuleDMPolicy

class PUfalRuleDM(PRuleDM):
    def __init__(self, cfg):
        cls_name = self.__class__.__name__
        self.db_cfg = cfg['DM'][cls_name]['db_cfg']  # database provider
        db = CamInfoDb(self.db_cfg)

        super(PUfalRuleDM, self).__init__(cfg, db)


def main():
    cfg = Config.load_configs(['resources/default-lz.cfg'],
                              use_default=False, project_root=True)
    #cfg = {'DM': {'UfalRuleDM':
    # {'ontology':"/xdisk/devel/vystadial/alex/applications/" + \
    #             "CamInfoRest/ontology.cfg",
    #  'db_cfg': "/xdisk/devel/vystadial/alex/applications/" + \
    #            "CamInfoRest/cued_data/CIRdbase_V7_noloc.txt"}}}
    u = UfalRuleDM(cfg)
    # ufal_ds = u.create_ds()
    while 1:
        curr_acts = DialogueActNBList()
        for ln in sys.stdin:
            if len(ln.strip()) == 0:
                break
            ln = ln.strip()
            print ln
            score, act = ln.split(" ", 1)
            score = float(score)
            curr_acts.add(score, DialogueActItem(dai=act))

        u.da_in(curr_acts)
        print "  >", u.da_out()

if __name__ == '__main__':
    main()
