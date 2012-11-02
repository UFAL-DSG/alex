#!/usr/bin/env python
# pylint: disable=E0602

from .ruledm import RuleDM, SystemRule, UserRule, Rule
from SDS.components.slu.da import DialogueAct

class UfalRuleDM(RuleDM):
    # STATE UPDATE RULES
    state_update_rules = [
        UserRule(
            da="request(X=y)",
            action=lambda X, y: {'rh_%s' % X: 'user-req'}
        ),
        SystemRule(
            da="inform(X)",
            cond=lambda state, X: state['rh_%s' % X] != None,
            action=lambda X: {'rh_%s' % X: 'user-req'}
        ),
        UserRule(
            da="confirm(X=y)",
            action=lambda X, y: {'ch_%s' % X: y}
        ),
        SystemRule(
            da="inform(X)",
            cond=lambda state, X: state['ch_%s' % X] != None,
            action=lambda X: {'ch_%s' % X: 'sys-inf'}
        ),
        UserRule(
            da="select(X=y)",
            action=lambda X, y: {'ch_%s' % X: [y]}
        ),
        UserRule(
            da="inform(X=y)",
            action=lambda X, y: {X: y}
        ),
    ]
"""
    # TRANSFORMATIONS
    transformation_rules = [
        # confirm responses
        UserTransformationRule(
            "affirm()",
            Rule(
                "confirm(X=y)",
                None,
                lambda: ["inform({0}={1})".format(X, y),]
            )
        ),
        UserTransformationRule(
            "negate()",
            Rule(
                "confirm(X=y)",
                None,
                lambda: ["deny({0}={1})".format(X, y),]
            )
        ),

        # don't care -> dontcare()
        UserTransformationRule(
            "inform(x=X)",
            Rule(
                None,
                lambda: X == "'dontcare'",
                lambda: ["dontcare()"]
            )
        ),

        # request responses
        UserTransformationRule(
            "affirm()",
            Rule(
                "request(x)",
                None,
                lambda: ["inform(%s='true')" % x]
            )
        ),
        UserTransformationRule(
            "deny()",
            Rule(
                "request(x)",
                None,
                lambda: ["inform(%s='false')" % x]
            )
        ),
        UserTransformationRule(
            "dontcare()",
            Rule(
                "request(x)",
                None,
                lambda: ["inform(%s='true')" % x]
            )
        ),
    ]
"""

def main():
    u = UfalRuleDM("SDS/applications/CamInfoRest/ontology.py")
    ufal_ds = u.create_ds()
    u.update(ufal_ds, DialogueAct("inform(area='barnwell')&inform(food_type='American')"))
    u.update(ufal_ds, DialogueAct("inform(name='test')"))
    u.update(ufal_ds, DialogueAct("inform(name='test')"))
    u.update(ufal_ds, DialogueAct("inform(name='test')"))
    u.update(ufal_ds, DialogueAct("inform(name='test')"))

if __name__ == '__main__':
    main()
