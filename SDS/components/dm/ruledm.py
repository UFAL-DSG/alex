#!/usr/bin/env python
#
# author: Lukas Zilka
#

import imp
import pprint

from SDS.components.slu.da import DialogueAct

RH_USER_REQUESTED = "user-requested"
CH_SYSTEM_INFORMED = RH_SYSTEM_INFORMED = "system-informed"


def _update_act_item(acts, da_item):
    action = acts[da_item.dat]
    action(da_item)


def _update_act(acts, da_):
    for da_item in da_:
        _update_act_item(acts, da_item)


class RuleDialogueState:
    slots = None

    USER_REQUESTED = "user-requested"

    def __init__(self, slots):
        self.slots = slots + \
            [self._get_rh_name(s) for s in slots] + \
            [self._get_sh1_name(s) for s in slots] + \
            [self._get_sh2_name(s) for s in slots] + \
            [self._get_ch_name(s) for s in slots]
        self.values = {s: None for s in self.slots}

        self.user_acts = self.build_user_acts()
        self.system_acts = self.build_system_acts()

    def build_user_acts(self):
        def inform(da_item):
            self._update_item_value(da_item.name, da_item.value)
            return True

        def deny(da_item):
            if self.values.get(da_item.name) == da_item.value:
                self._update_item_value(da_item.name, None)
                return True
            else:
                return False

        def request(da_item):
            self._update_item_value(self._get_rh_name(da_item.name),
                                    RH_USER_REQUESTED)

        def confirm(da_item):
            self._update_item_value(self._get_ch_name(da_item.name),
                                    da_item.value)

        return {
            'inform': inform,
            'deny': deny,
            'request': request,
            'confirm': confirm,
        }

    def build_system_acts(self):
        def inform(da_item):
            if self.values.get(self._get_rh_name(da_item.name)) == \
                    RH_USER_REQUESTED:
                self._update_item_value(self._get_rh_name(da_item.name),
                                        RH_SYSTEM_INFORMED)

            if self.values.get(self._get_ch_name(da_item.name)) is not \
                    None:
                self._update_item_value(self._get_ch_name(da_item.name),
                                        CH_SYSTEM_INFORMED)

            return True

        def deny(da_item):
            if self.values.get(self._get_ch_name(da_item.name)) is not \
                    None:
                self._update_item_value(self._get_ch_name(da_item.name),
                                        CH_SYSTEM_INFORMED)

            return True

        return {
            'inform': inform,
            'deny': deny,
        }

    def _update_item_check(self, key):
        assert key in self.slots

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

    def _update_item_value(self, key, value):
        self._update_item_check(key)
        self.values[key] = value

    def update_user(self, da_):
        _update_act(self.user_acts, da_)

    def update_system(self, da_):
        _update_act(self.system_acts, da_)

    def copy(self, ds_):
        self.slots = list(ds_.slots)
        self.values = dict(ds_.values.items())

    def __unicode__(self):
        vals = pprint.pformat(self.values)
        return vals

    def __str__(self):
        return unicode(self)


class RuleDM:
    def __init__(self, ontology_file):
        self.ontology = imp.load_source('ontology', ontology_file)

    def update(self, curr_ds, da):
        new_ds = self.create_ds()
        new_ds.copy(curr_ds)
        new_ds.update_user(da)

    def create_ds(self):
        res = RuleDialogueState(self.ontology.slots.keys())
        return res


if __name__ == '__main__':
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
