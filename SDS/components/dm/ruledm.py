#!/usr/bin/env python
#
# author: Lukas Zilka
#


import imp
import re
import pprint
from collections import defaultdict

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
PLACE_INFORMED_SLOT = "__placeinformed"
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
                        new_dais += [DialogueActItem().parse(new_dai)]
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

    def reset_changes(self):
        self.values[CHANGES_SLOT] = []

    def copy(self, ds_):
        self.slots = list(ds_.slots)
        self.values = dict(ds_.values.items())

    def clear(self):
        for key in self.slots:
            self.slots[key] = None

    def __unicode__(self):
        vals = pprint.pformat({k: v for k, v in self.values.items() if v is not None})
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
        self.values = self.db.get_possible_values()
        self.ontology_unknown_re = re.compile(r"^.*-([0-9]+)")

    def build_query(self, state):
        query = {}
        for slot in self.slots:
            if state[slot] != None:
                query[slot] = state[slot]

        return query

    def query_db(self, state):
        query = self.build_query(state)
        return self.db.get_matching(query)

    def user_has_specified_something(self, state):
        return len(self.build_query(state)) > 0

    def filter(self, in_da):
        new_nblist = DialogueActNBList()
        for item in in_da:
            da = item[1]
            new_da = DialogueAct()
            for dai in da:
                if dai.dat in ["inform", "request"]:
                    if dai.value is not None and not dai.value in self.values:
                        continue
                if dai.dat in ["inform", "request", "confirm"]:
                    if not dai.name in self.slots:
                        continue

                if type(dai.value) is str and self.ontology_unknown_re.match(dai.value):
                    continue


                if dai.dat in ["inform", "request", "other",
                               "confirm", "reqalts"]:
                    new_da.append(dai)

            if item[0] >= 0.5:  # do not consider things bellow 0.5
                if len(new_da) > 0:
                    new_nblist.add(item[0], new_da)
        return new_nblist

    def get_interesting_slot(self, state):
        return state[CHANGES_SLOT][0]

    def say_bye(self):
        return DialogueAct("bye()")

    def say_hello(self):
        return DialogueAct("hello()")

    def say_instructions(self):
        return DialogueAct("instructions()")

    def say_nomatch(self):
        return DialogueAct("nomatch()")

    def say_query(self, state):
        query = self.build_query(state)
        act = "&".join(["wants(%s=%s)" % (k, v,) for k, v in query.items()])
        return DialogueAct(act)

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

    def say_noentiendo(self):
        return DialogueAct("noentiendo()")

    def answer_confirm(self, state, res0, slots_to_confirm):
        conflicts = []
        selects = []
        noclues = []
        for ch_slot, slot_value in slots_to_confirm.items():
            slot = state.chkey_to_key(ch_slot)
            print "SLOT VAL:", slot_value
            state.update({ch_slot: None})

            if not slot in res0:
                noclues += [slot]
            elif not res0[slot].lower() in slot_value:
                conflicts += [slot]
                if len(slot_value) > 1:
                    selects += [(slot, res0[slot], )]

        if len(noclues) > 0:
            return DialogueAct(
                "&".join(["noclue(%s)" % n for n in noclues]))
        elif len(conflicts) == 0:
            if len(selects) == 0:
                return DialogueAct("affirm()")
            else:
                return DialogueAct(
                    "&".join(["confirm(%s=%s)" % (n, v, ) for n, v in selects]))
        else:
            conf_acts = []
            for conflict in conflicts:
                conf_acts += ["inform(%s='%s')" % (conflict, res0[conflict], ) ]
            res = DialogueAct("negate()")
            res.merge(DialogueAct("&".join(conf_acts)))
            return res

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

    def get_understood_dat(self, user_da):
        pass

    def dat_contains(self, what, dat):
        if dat is None:
            return False
        for _, dai in dat:
            if dai.dat == what:
                return True

        return False

    def get_da(self, state, user_da):
        if len(state[CHANGES_SLOT]) > 0:
            state.update({PLACE_INFORMED_SLOT: False})

        # if it is the first turn, say hello
        if user_da is None:
            return state, self.say_hello()

        if user_da.has_dat("bye"):
            return state, self.say_bye()

        if user_da.has_dat("restart"):
            state.clear()

        # if we didn't understand tell him
        if len(user_da) == 0 or user_da.has_dat("null"):
            return state, self.say_noentiendo()

        # if the user hasn't specified anything (i.e. blank filter)
        # tell him what he can do
        if not self.user_has_specified_something(state):
            return state, self.say_instructions()

        res = self.query_db(state)
        slots_to_say = self.get_slots_to_say(state)
        slots_to_confirm = self.get_slots_to_confirm(state)
        was_bad_slot = self.get_bad_slot(state)
        res_da = None

        #u_dat = self.get_understood_dat(user_da)
        user_dat = user_da # user_da[-1].dat if user_da is not None else None

        # state updates
        if user_da.has_dat("reqalts"):
            state.update({ALTS_SLOT: [True]})

        res0 = self.pick_record(state, res)
        # if nothing matches, tell him
        if res0 is None:
            da = self.say_nomatch()
            da.merge(self.say_query(state))
            return state, da

        print "USER DA:", user_da, user_da is not None and len(user_da)
        print "STATE:", state
        print "CNT(RES):", len(res)
        print "RES0:", res0
        print "REQ SLOTS:", slots_to_say

        # if the user requested something, tell him immediatelly
        if len(slots_to_say) > 0:
            if not 'name' in slots_to_say and \
               state['rh_name'] != "system-informed":
                slots_to_say += ['name']
            res_da = self.say_slots(state, res0, slots_to_say)
            return state, res_da

        # if not, be ready to tell him something useful
        if len(slots_to_say) == 0 and not state[PLACE_INFORMED_SLOT]:
            slots_to_say = ['name', 'food']
            sink_da = self.say_slots(state, res0, slots_to_say)
            # sink_da.append(DialogueActItem().parse("match()"))
        else:
            sink_da = DialogueAct("anythingelse()")

        if len(slots_to_confirm) > 0:
            res_da = self.answer_confirm(state, res0, slots_to_confirm)
            return state, res_da

        state.update({PLACE_INFORMED_SLOT: True})
        return state, sink_da




    def get_da_old(self, state, user_da):
        res = self.query_db(state)
        slots_to_say = self.get_slots_to_say(state)
        slots_to_confirm = self.get_slots_to_confirm(state)
        was_bad_slot = self.get_bad_slot(state)
        res_da = None

        #u_dat = self.get_understood_dat(user_da)
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
            state.update({BADSLOT_SLOT: None})
        elif len(slots_to_confirm) > 0:
            res_da = self.answer_confirm(state, res0, slots_to_confirm)
        elif len(slots_to_say) > 0:
            res_da = self.say_slots(state, res0, slots_to_say)
        else:
            if res0 is not None:
                res_da = self.say_inform(state, res0)
            else:
                res_da = DialogueAct("nomatch()")
            #res_da.append(DialogueActItem().parse("count(%d)" % len(res)))

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
        self.policy = self.policy_cls(self.ontology.slots.keys(),
                                      db_cfg)
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
                pass
                #new_ds.update({BADSLOT_SLOT: True})


        return new_ds

    def update(self, curr_ds, nbda, last_da=None):
        #new_ds = self._process_rules(curr_ds, da, last_da)
        new_ds = self.create_ds()
        new_ds.copy(curr_ds)

        assigned_something = False
        breaking = False
        update_history = set()
        for score, da in nbda:
            for act in da:
                if act.dat == "other" and assigned_something:
                    breaking = True
                    break

                print update_history
                if act.name in update_history:
                    continue

                if act.dat == "inform":
                    new_ds.update({act.name: act.value})
                    update_history.add(act.name)
                    assigned_something = True
                elif act.dat == "request":
                    new_ds.update({"rh_%s" % act.name: "user-requested"})
                    update_history.add(act.name)
                    assigned_something = True
                elif act.dat == "confirm":
                    new_ds.update({"ch_%s" % act.name: [act.value]})
                    update_history.add(act.name)
                    assigned_something = True

            if breaking:
                break

        return new_ds

    def create_ds(self):
        res = RuleDialogueState(self.ontology.slots.keys())
        return res

    def pick_best_da(self, das):
        if isinstance(das, DialogueActNBList):
            return sorted(das, key=lambda x: -x[0])[0][1]
        elif isinstance(das, DialogueActConfusionNetwork):
            return das.get_best_nonnull_da()
        else:
            raise Exception('unknown input da of type: %s' % str(das.__class__))

    def da_in(self, in_da):
        print "in_da", in_da

    def da_out(self):
        print 'nothing'

    def da_in(self, in_da):
        if isinstance(in_da, DialogueActConfusionNetwork):
            in_da = in_da.get_da_nblist()

        filtered_da = self.policy.filter(in_da)
        #da = self.pick_best_da(in_da)
        self.cfg['Logging']['system_logger'].debug("RuleDM: Using this DA: %s" % str(filtered_da) )

        self.dstate.reset_changes()
        self.dstate = self.update(self.dstate, filtered_da)
        self.last_usr_da = filtered_da

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
