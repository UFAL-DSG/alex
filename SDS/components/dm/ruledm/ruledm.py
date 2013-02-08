#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008/.
"""
.. module:: ruledm
    :synopsis: Rule-based dialogue manager implementation.

.. moduleauthor:: Lukas Zilka <zilka@ufal.mff.cuni.cz>
"""
import imp

if __name__ == '__main__':
    import autopath

from SDS.components.dm.ruledm.druledmpolicy import (
    DRuleDMPolicy,
    DRuleDS
)
from SDS.components.dm import DialogueManager
from SDS.components.slu.da import (
    DialogueAct,
    DialogueActItem,
    DialogueActConfusionNetwork,
    DialogueActNBList
)


class RuleDM(DialogueManager):
    """Simple Rule Dialogue Manager.

    You can override policy_cls and dstste_cls fields to implement new
    behavior.

    policy_cls implements IRuleDMPolicy
    dstate_cls implements IRuleDS
    """

    policy_cls = DRuleDMPolicy
    dstate_cls = DRuleDS

    def __init__(self, cfg):
        super(RuleDM, self).__init__(cfg)

        # save class name (useful for configuration of inherited classes)
        cls_name = self.__class__.__name__

        # load configuration
        ontology = cfg['DM'][cls_name]['ontology']  # data ontology
        db_cfg = cfg['DM'][cls_name]['db_cfg']  # database provider

        # for evaluation - loads a code from a url and say it to the user
        self.provide_code = cfg['DM'][cls_name]['provide_code']
        self.code_submit_url = cfg['DM'][cls_name]['code_submit_url']

        self.ontology = imp.load_source('ontology', ontology)

        self.dstate = self.create_ds()
        self.policy = self.policy_cls(self.ontology.slots.keys(),
                                      db_cfg)
        self.last_usr_da = None
        self.da_history = []

    def filter(self, in_da):
        """Go through the input dialogue acts and pick only the ones
        that we can understand and that have good enough confidence."""

        new_nblist = DialogueActNBList()

        # for each dialogue act item check if it is of known type
        # and if it has good probability
        for item in in_da:
            da = item[1]
            new_da = DialogueAct()
            for dai in da:
                if dai.dat in ["inform", "request"]:
                    if dai.value is not None and not dai.value in self.policy.values:
                        continue
                if dai.dat in ["inform", "request", "confirm"]:
                    if not dai.name in self.policy.slots:
                        continue

                # check if the value is in our ontology
                #if type(dai.value) is str and \
                #        self.ontology_unknown_re.match(dai.value):
                #    continue

                if dai.dat in ["inform", "request", "other",
                               "confirm", "reqalts", "bye",
                               "restart"]:
                    new_da.append(dai)

            if item[0] >= 0.3:  # do not consider things bellow 0.3
                if len(new_da) > 0:
                    new_nblist.add(item[0], new_da)

        return new_nblist

    def update(self, curr_ds, nbda):
        """Update dialogue state from the N-Best list of Dialogue Acts"""
        #new_ds = self.create_ds()
        #new_ds.copy(curr_ds)
        new_ds = curr_ds

        assigned_something = False
        breaking = False
        update_history = set()
        for score, da in nbda:
            for act in da:
                if act.dat == "other" and assigned_something:
                    breaking = True
                    break

                if act.name in update_history:
                    continue

                now_assigned_something = True

                if act.dat == "inform":
                    new_ds.update_user({act.name: act.value}, score)
                    update_history.add(act.name)
                elif act.dat == "request":
                    new_ds.update_user_request({act.name: False}, score)
                    update_history.add(act.name)
                elif act.dat == "confirm":
                    new_ds.update_user_confirm({act.name: [act.value]}, score)
                    update_history.add(act.name)
                elif act.dat == "reqalts":
                    new_ds.update_user_alternative()
                else:
                    now_assigned_something = False

                if now_assigned_something:
                    assigned_something = True


            if breaking:
                break

        return new_ds

    def create_ds(self):
        """Create new dialogue state."""
        res = self.dstate_cls(self.ontology.slots.keys())
        return res

    def da_in(self, in_da):
        """Process user's Dialogue Act."""

        # we cannot process confusion networks so if we got one, transform it
        # to an nbest list
        if isinstance(in_da, DialogueActConfusionNetwork):
            in_da = in_da.get_da_nblist()

        # preprocess the input and leave only relevant things that we understand
        # HACK ALERT: it should not be needed if SLU is built specifically for this DM
        filtered_da = self.filter(in_da)


        self.cfg['Logging']['system_logger'].debug(
            "RuleDM: Using this DA:\n{da!s} \n#########".format(da=filtered_da))

        # update dialogue state according to the input
        self.dstate.new_turn()
        self.dstate.new_da(filtered_da)
        self.dstate = self.update(self.dstate, filtered_da)

    def da_out(self):
        """Get system's Dialogue Act."""
        self.dstate, new_da = self.policy.get_da(self.dstate)

        if self.provide_code and new_da.has_dat("bye"):
            code = self.get_token()
            new_da.append(DialogueActItem(dai="code(%s)" % code))

        return new_da

    def new_dialogue(self):
        self.dstate = self.create_ds()

    def end_dialogue(self):
        pass


if __name__ == '__main__':
    s = RuleDS(['name', 'addr'])
    s.update_user({'name': "asdf"}, 0.1)
    s.update_user({'name': "fdsa"}, 0.4)
    print s

