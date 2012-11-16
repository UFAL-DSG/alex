#!/usr/bin/env python
#
# author: Lukas Zilka
#


import imp
import pprint

from SDS.components.dm import DialogueManager
from SDS.components.slu.da import DialogueActItem, DialogueAct, \
                                  DialogueActConfusionNetwork, \
                                  DialogueActNBList

RH_USER_REQUESTED = "user-requested"
CH_SYSTEM_INFORMED = RH_SYSTEM_INFORMED = "system-informed"
LDA_SLOT = "__lda"
ALTS_SLOT = "__alts"
CHANGES_SLOT = "__changes"
BADSLOT_SLOT = "__badslot"
SLOT_REQ = "rh"
SLOT_CONFIRM = "ch"



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
            [self.get_rh_name(s) for s in slots] + \
            [self._get_sh1_name(s) for s in slots] + \
            [self._get_sh2_name(s) for s in slots] + \
            [self.get_ch_name(s) for s in slots] + \
            [LDA_SLOT, ALTS_SLOT, CHANGES_SLOT, BADSLOT_SLOT]
        self.values = {s: None for s in self.slots}
        self.values[ALTS_SLOT] = []
        self.values[CHANGES_SLOT] = [None]

    def update(self, new_values):
        for key, value in new_values.items():
            if not type(value) is list:
                self.values[key] = value
                if not key.startswith(SLOT_REQ + "_") and \
                   not key.startswith(SLOT_CONFIRM + "_"):
                    self.values[CHANGES_SLOT].insert(0, key)
                print 'setting', key, value
            else:
                if self.values[key] is None:
                    self.values[key] = []
                assert type(self.values[key]) is list
                self.values[key] += value

    def copy(self, ds_):
        self.slots = list(ds_.slots)
        self.values = dict(ds_.values.items())

    def clear(self):
        for key in self.slots:
            self.slots[key] = None

    def __unicode__(self):
        vals = pprint.pformat(self.values)
        return vals

    def __str__(self):
        return unicode(self)

    @classmethod
    def get_rh_name(cls, name):
        return "%s_%s" % (SLOT_REQ, name,)

    @classmethod
    def _get_sh1_name(cls, name):
        return "sh1_%s" % name

    @classmethod
    def _get_sh2_name(cls, name):
        return "sh2_%s" % name


    @classmethod
    def get_ch_name(cls, name):
        return "%s_%s" % (SLOT_CONFIRM, name,)

    def __getitem__(self, key):
        return self.values[key]

    def get(self, key, default=None):
        return self.values.get(key, default)

    def keys(self, prefix=None):
        return [x for x in self.values.keys() if prefix is None or x.startswith("%s_" % prefix)]

    def reqkey_to_key(self, req_key):
        return req_key[len(SLOT_REQ) + 1:]

    def chkey_to_key(self, req_key):
        return req_key[len(SLOT_REQ) + 1:]


class RuleDMPolicy:
    def __init__(self, slots, db_cfg):
        self.db = self.db_cls(db_cfg)
        self.slots = slots

    def query_db(self, state):
        query = {}
        for slot in self.slots:
            if state[slot] != None:
                query[slot] = state[slot]

        return self.db.get_matching(query)

    def say_bye(self):
        return DialogueAct("bye()")

    def say_hello(self):
        return DialogueAct("hello()")

    def get_interesting_slot(self, state):
        return state[CHANGES_SLOT][0]

    def say_inform(self, state, rec):
        islot_name = self.get_interesting_slot(state) or self.slots[0]
        if not islot_name in rec:
            islot_name = rec.keys()[0]
        slot_name = 'name'
        return DialogueAct(
            "inform(%s='%s')&inform(%s='%s')" % \
            (slot_name, rec[slot_name], islot_name, rec[islot_name])
        )

    def say_slots(self, state, res0, slots_to_say):
        d_str = []
        for slot in slots_to_say:
            d_str += ["inform(%s='%s')" % (slot, res0.get(slot, 'dontknow'), )]
            state.update({state.get_rh_name(slot): CH_SYSTEM_INFORMED})

        return DialogueAct("&".join(d_str))

    def answer_confirm(self, state, res0, slots_to_confirm):
        conflicts = []
        for ch_slot, slot_value in slots_to_confirm.items():
            state.update({ch_slot: None})
            slot = state.chkey_to_key(ch_slot)
            if res0[slot] != slot_value:
                conflicts += [slot]

        if len(conflicts) == 0:
            return DialogueAct("affirm()")
        else:
            conf_acts = []
            for conflict in conflicts:
                conf_acts += ["inform(%s='%s')" % (conflict, res0[conflict], ) ]
            return DialogueAct("negate()&" + "&".join(conf_acts))

    def say_bad_slot(self):
        return DialogueAct("sorry()&badslot()")

    def pick_record(self, state, res):
        ndx = len(state.get(ALTS_SLOT, []))
        if len(res) > ndx:
            return res[ndx]
        elif len(res) > 0:
            return res[0]
        else:
            return None

    def get_slots_to_say(self, state):
        keys = state.keys(SLOT_REQ)
        slots = [state.reqkey_to_key(key) for key in keys
                 if not state[key] in [None, CH_SYSTEM_INFORMED]]
        return slots

    def get_slots_to_confirm(self, state):
        keys = state.keys(SLOT_CONFIRM)
        slots = {key: state[key] for key in keys if state[key] is not None}
        return slots

    def get_bad_slot(self, state):
        return state[BADSLOT_SLOT] is not None

    def get_da(self, state, user_da):
        res = self.query_db(state)
        slots_to_say = self.get_slots_to_say(state)
        slots_to_confirm = self.get_slots_to_confirm(state)
        was_bad_slot = self.get_bad_slot(state)
        res_da = None
        user_dat = user_da[-1].dat if user_da is not None else None

        # state updates
        if user_dat == "reqalts":
            state.update({ALTS_SLOT: [True]})
        elif user_dat == "restart":
            state.clear()

        res0 = self.pick_record(state, res)

        # determinig what to say
        if user_dat == "hello" or user_dat is None:
            res_da = self.say_hello()
        elif user_dat == "bye":
            res_da = self.say_bye()
        elif user_dat == "repeat":
            res_da = None
        elif was_bad_slot:
            res_da = self.say_bad_slot()
        elif len(slots_to_confirm) > 0:
            res_da = self.answer_confirm(state, res0, slots_to_confirm)
        elif len(slots_to_say) > 0:
            res_da = self.say_slots(state, res0, slots_to_say)
        else:
            if res0 is not None:
                res_da = self.say_inform(state, res0)
            else:
                res_da = DialogueAct("nomatch()")
            res_da.append(DialogueActItem().parse("count(%d)" % len(res)))

        return state, res_da

from SDS.utils.interface import Interface, interface_method

class IDM(Interface):
    def update(self, curr_ds, da, last_da):
        pass


class RuleDM(DialogueManager):
    state_update_rules = None
    transformation_rules = None
    policy_cls = None

    def __init__(self, cfg):
        self.cfg = cfg
        cls_name = self.__class__.__name__

        ontology = cfg['DM'][cls_name]['ontology']
        db_cfg = cfg['DM'][cls_name]['db_cfg']

        self.ontology = imp.load_source('ontology', ontology)

        for i, rule in enumerate(self.state_update_rules):
            rule.id = i

        self.dstate = self.create_ds()
        self.policy = self.policy_cls(self.ontology.slots.keys(), db_cfg)
        self.last_usr_da = None
        self.last_sys_da = None

    def _process_rules(self, state, da, last_da):
        new_ds = self.create_ds()
        new_ds.copy(state)

        new_da = da
        for trule in self.transformation_rules:
            new_da = trule.eval(new_da, last_da, state)

        for rule in self.state_update_rules:
            try:
                new_vals = rule.eval(da, state)
                for new_val in new_vals:
                    if new_val is not None:
                        new_ds.update(new_val)
            except KeyError:
                new_ds.update({BADSLOT_SLOT: True})


        return new_ds

    def update(self, curr_ds, da, last_da=None):
        new_ds = self._process_rules(curr_ds, da, last_da)
        return new_ds

    def create_ds(self):
        res = RuleDialogueState(self.ontology.slots.keys())
        return res

    def pick_best_da(self, das):
        if isinstance(das, DialogueActNBList):
            return sorted(das, key=lambda x: -x[0])[0][1]
        elif isinstance(das, DialogueActConfusionNetwork):
            return das.get_best_da()
        else:
            raise Exception('unknown input da of type: %s' % str(das.__class__))



    def da_in(self, in_da):
        da = self.pick_best_da(in_da)
        self.cfg['Logging']['system_logger'].debug("RuleDM: Using this DA: %s" % str(da) )

        self.dstate = self.update(self.dstate, da)
        self.last_usr_da = da

    def da_out(self):
        self.dstate, new_da = self.policy.get_da(self.dstate, self.last_usr_da)
        if new_da is not None:
            self.last_sys_da = new_da

        return self.last_sys_da

    def new_dialogue(self):
        self.dstate = self.create_ds()
        self.last_usr_da = None

    def end_dialogue(self):
        pass

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
