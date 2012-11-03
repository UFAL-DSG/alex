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


class TransformationRule(object):
    def __init__(self, da=None, last_da=None, cond=None, t=None):
        self.da = da
        self.last_da = last_da
        self.cond = cond
        self.t = t

    def _cond_matches(self, da, last_da, state):
        if self.cond is not None:
            res = self.cond(da, last_da, state)
            assert type(res) is bool
            return res
        else:
            return True

    def eval(self, da, last_da, state):
        new_dais = []
        consumed_dais = []
        if last_da is None:
            last_da = [None]

        for dai in da:
            for last_dai in last_da:
                if self.da is not None and dai.dat != self.da:
                    continue
                if self.last_da is not None and \
                   (last_dai is None or last_dai.dat != self.last_da):
                    continue

                if self._cond_matches(dai, last_dai, state):
                    new_dai = self.t(dai, last_dai)
                    if new_dai is not None:
                        new_dais += [DialogueActItem.parse(new_dai)]
                        consumed_dais += [dai]

        for new_dai in new_dais:
            da.append(new_dai)

        return da



class UserTransformationRule(TransformationRule):
    pass

class SystemTransformationRule(TransformationRule):
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
        self.da = da
        self.cond, self.action = cond, action
        self.iter_apply = True

    def _cond_matches(self, dai, state):
        if self.cond is not None:
            res = self.cond(dai, state)
            assert type(res) is bool
            return res
        else:
            return True

    def _action(self, dai):
        print 'executing action of', self.da, self.cond
        res = self.action(dai)
        return res

    def eval(self, da, state):
        res = []
        for dai in da:
            if self.da is not None and dai.dat != self.da:
                continue

            if self._cond_matches(dai, state):
                res += [self._action(dai)]

        return res

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

    def _process_rules(self, state, da, last_da):
        new_ds = self.create_ds()

        new_da = da
        for trule in self.transformation_rules:
            new_da = trule.eval(new_da, last_da, state)

        for rule in self.state_update_rules:
            new_vals = rule.eval(da, state)
            for new_val in new_vals:
                if new_val is not None:
                    new_ds.update(new_val)

        return new_ds

    def update(self, curr_ds, da, last_da=None):
        new_ds = self._process_rules(curr_ds, da, last_da)
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
