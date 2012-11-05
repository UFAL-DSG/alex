#!/usr/bin/env python
#
# author: Lukas Zilka
#

import imp
import inspect
import pprint

from SDS.components.slu.da import DialogueActItem, DialogueAct

RH_USER_REQUESTED = "user-requested"
CH_SYSTEM_INFORMED = RH_SYSTEM_INFORMED = "system-informed"
LDA_SLOT = "__lda"


def _update_act_item(acts, da_item):
    action = acts[da_item.dat]
    action(da_item)


def _update_act(acts, da_):
    for da_item in da_:
        _update_act_item(acts, da_item)


class Trigger(object):
    def __init__(self):
        raise NotImplementedError("abstract class")


class RuleTrigger(Trigger):
    def __init__(self, t, n, v):
        self.da_type = t
        self.slot_name = n
        self.slot_value = v

    def match(self, da):
        """Determine whether the trigger will fire by matching
        its condition with the da content"""

        for da_item in da:
            if self.da_type is not None:
                if not (da_item.dat == self.da_type):
                    return False

            if self.slot_name is not None:
                if not (da_item.name == self.slot_name):
                    return False

            if self.slot_value is not None:
                if not (da_item.value == self.slot_value):
                    return False

        return True


class TransformationRule(object):
    def __init__(self):
        pass


def _da_match_pattern(da_item, pattern):
    if pattern.dat is not None:
        if not (da_item.dat == pattern.dat):
            return False

    if pattern.name is not None:
        if not (da_item.name == pattern.name):
            return False

    if pattern.value is not None:
        if not (da_item.value == pattern.value):
            return False

    return True


class Rule(object):
    def __init__(self, da=None, cond=None, action=None):
        self.da = DialogueActItem().parse(da)
        self.cond, self.action = cond, action

    def _da_extract(self, da):
        "Find out if at least one dai matches the pattern dai for this rule."
        if self.da is not None:
            if da_item.dat == self.da.dat:
                res = {}
                if self.da.name is not None:
                    res[self.da.name] = da_item.name
                if self.da.value is not None:
                    res[self.da.value] = da_item.value
                return res
        return None

    def _cond_matches(self, da_vals, state):
        if self.cond is not None:
            res = self.cond(state, **da_vals)
            assert type(res) is bool
            return res
        else:
            return True

    def _action(self, da_vals):
        print 'executing action of', self.da, self.cond
        res = self.action(**da_vals)
        return res

    def eval(self, da, state):
        da_vals = self._da_extract(da)
        if da_vals is not None:
            if self._cond_matches(da_vals, state):
                return self._action(da_vals)
            return None
        else:
            return None

class UserRule(Rule):
    pass


class SystemRule(Rule):
    pass


class RuleDialogueState:
    slots = None

    def __init__(self, slots):
        self.slots = slots + \
            [self._get_rh_name(s) for s in slots] + \
            [self._get_sh1_name(s) for s in slots] + \
            [self._get_sh2_name(s) for s in slots] + \
            [self._get_ch_name(s) for s in slots] + \
            [LDA_SLOT]
        self.values = {s: None for s in self.slots}

    def update(self, new_values):
        for key, value in new_values.items():
            if not type(value) is list:
                self.values[key] = value
                print 'setting', key, value
            else:
                if self.values[key] is None:
                    self.values[key] = []
                assert type(self.values[key]) is list
                self.values[key] += value

    def copy(self, ds_):
        self.slots = list(ds_.slots)
        self.values = dict(ds_.values.items())

    def __unicode__(self):
        vals = pprint.pformat(self.values)
        return vals

    def __str__(self):
        return unicode(self)

    @classmethod
    def _get_rh_name(cls, name):
        return "rh_%s" % name

    @classmethod
    def _get_sh1_name(cls, name):
        return "sh1_%s" % name

    @classmethod
    def _get_sh2_name(cls, name):
        return "sh2_%s" % name


    @classmethod
    def _get_ch_name(cls, name):
        return "ch_%s" % name

    def __getitem__(self, key):
        return self.values[key]


class RuleDM:
    state_update_rules = None
    transformation_rules = None

    def __init__(self, ontology_file):
        self.ontology = imp.load_source('ontology', ontology_file)

        for i, rule in enumerate(self.state_update_rules):
            rule.id = i

    def _process_rules(self, state, user_da):
        new_ds = self.create_ds()

        for rule in self.state_update_rules:
            new_vals = rule.eval(user_da, state)
            if new_vals is not None:
                new_ds.update(new_vals)

        return new_ds

    def update(self, curr_ds, da):
        new_ds = self._process_rules(curr_ds, da)
        return new_ds

    def create_ds(self):
        res = RuleDialogueState(self.ontology.slots.keys())
        return res

def main():
    dm = RuleDM("applications/CamInfoRest/ontology.py")
    ds = dm.create_ds()
    da = DialogueAct("inform(venue_type='pub')&inform(price_range='cheap')")
    ds.update_user(da)
    print da
    print ds
    da = DialogueAct("inform(food_type='Chinese')")
    ds.update_user(da)
    print da
    print ds
    da = DialogueAct("deny(food_type='Chinese')")
    ds.update_user(da)
    print da
    print ds
    da = DialogueAct("request(food_type)")
    ds.update_user(da)
    print da
    print ds
    da = DialogueAct("inform(food_type='Chinese')&inform(price_range='cheap')")
    ds.update_system(da)
    print da
    print ds
    da = DialogueAct("confirm(price_range='cheap')")
    ds.update_user(da)
    print da
    print ds


if __name__ == '__main__':
    #main()
    main2()
