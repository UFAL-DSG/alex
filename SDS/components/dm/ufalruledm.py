#!/usr/bin/env python
# pylint: disable=E0602

import sys
import autopath
from SDS.components.dm.ruledm import RuleDM, RuleDMPolicy
from SDS.components.dm.ruledm import SystemRule, UserRule
from SDS.components.dm.ruledm import UserTransformationRule

from SDS.components.slu.da import DialogueActItem, DialogueActHyp, DialogueActNBList
from SDS.utils.caminfodb import CamInfoDb
from SDS.utils.config import Config

class UfalRuleDMPolicy(RuleDMPolicy):
    db_cls = CamInfoDb

class UfalRuleDM(RuleDM):
    policy_cls = UfalRuleDMPolicy

    # STATE UPDATE RULES
    state_update_rules = [
        UserRule(
            da="deny",
            action=lambda da: {da.name: None}
        ),
        UserRule(
            da="request",
            action=lambda da: {'rh_%s' % da.name: 'user-req'}
        ),
        SystemRule(
            da="inform",
            cond=lambda da, state: state['rh_%s' % da.name] != None,
            action=lambda da: {'rh_%s' % da.name: 'user-req'}
        ),
        UserRule(
            da="confirm",
            action=lambda da: {'ch_%s' % da.name: da.value}
        ),
        SystemRule(
            da="inform",
            cond=lambda da, state: state['ch_%s' % da.name] != None,
            action=lambda da: {'ch_%s' % da.name: 'sys-inf'}
        ),
        UserRule(
            da="select",
            action=lambda da: {'ch_%s' % da.nameX: [da.value]}
        ),
        UserRule(
            da="inform",
            action=lambda da: {da.name: da.value}
        )
    ]

    # TRANSFORMATIONS
    transformation_rules = [
        # confirm responses
        UserTransformationRule(
            da="affirm",
            last_da="confirm",
            t=lambda da, last_da: "inform({0}={1})".format(da.name, da.value)
        ),
        UserTransformationRule(
            da="negate",
            last_da="confirm",
            t=lambda da, last_da: "deny({0}={1})".format(da.name, da.value),
        ),

        # don't care -> dontcare()
        UserTransformationRule(
            da="inform",
            cond=lambda da, last_da, state: da.value == "dontcare",
            t=lambda da, last_da: "dontcare()"
        ),

        # request responses
        UserTransformationRule(
            da="affirm",
            last_da="request",
            t=lambda da, last_da: "inform(%s='true')" % last_da.name
        ),
        UserTransformationRule(
            da="deny",
            last_da="request",
            t=lambda da, last_da: "inform(%s='false')" % last_da.name
        ),
        UserTransformationRule(
            da="dontcare",
            last_da="request",
            t=lambda da, last_da: "inform(%s='true')" % last_da.name
        ),
    ]


def main():
    import autopath
    cfg = Config('resources/default-lz.cfg', True)
    #cfg = {'DM': {'UfalRuleDM': {'ontology':"/xdisk/devel/vystadial/SDS/applications/CamInfoRest/ontology.cfg", 'db_cfg': "/xdisk/devel/vystadial/SDS/applications/CamInfoRest/cued_data/CIRdbase_V7_noloc.txt"}}}
    u = UfalRuleDM(cfg)
    ufal_ds = u.create_ds()
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

