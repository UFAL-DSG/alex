#!/usr/bin/env python
# encoding: utf8

"""
.. module:: ruledm
    :synopsis: Probabilistic Rule-based dialogue manager implementation.

.. moduleauthor:: Lukas Zilka <zilka@ufal.mff.cuni.cz>
"""

import re
import random

if __name__ == '__main__':
    import autopath

from collections import defaultdict

from alex.components.dm import DialogueManager
from alex.components.dm.ruledm.iruleds import IRuleDS
from alex.components.dm.pstate import PDDiscrete, PDDiscreteOther
from alex.utils.enums import enum
from alex.components.slu.da import (
    DialogueAct,
    DialogueActItem,
    DialogueActConfusionNetwork
    )

RequestSlotValue = enum(user_requested=1, system_provided=2)
ResetSlotValue = enum(yes=1, done=2)
OtherSlotValue = enum(yes=1, done=2)
ByeSlotValue = enum(yes=1, done=2)
AltsSlotValue = enum(yes=1, done=2)
ConfirmSlotValue = enum(done=2)
HelloSlotValue = enum(done=2)
FilterSlotValue = enum(started_filtering=1, filtering=2, stopped_filtering=3)

Action = enum(
    # meta
    Hello=1, Bye=2, Reset=3, NoEntiendo=4, Instructions=5, Alts=6,
    # db action
    Confirm=7, Provide=8, Inform=9, NoMatch=10, ChangeFilter=11
    )


class SystemAction(object):
    def __init__(self, action, params=None):
        self.action = action
        self.params = params

    def __repr__(self):
        return "%s %s" % (Action.reverse_mapping[self.action],
                          str(self.params), )


class SimpleSlotUpdater(object):
    @classmethod
    def update_slot(cls, curr_pd, observ_pd):
        observed_items = observ_pd.get_items()
        new_pd = PDDiscrete()

        items = set(curr_pd.get_items() + observed_items)
        for item in items:
            new_pd[item] = curr_pd[item] * observ_pd[None]
            if item is not None:
                new_pd[item] += observ_pd[item]

        return new_pd

class ExtendedSlotUpdater(object):
    @classmethod
    def update_slot(cls, curr_pd, observ_pd, deny_pd=None):
        if deny_pd is None:
            deny_pd = PDDiscreteOther()
        observed_items = observ_pd.get_items()
        observed_items += deny_pd.get_items()
        new_pd = PDDiscrete()

        p_stay = 1.0 #2.2

        items = set(curr_pd.get_items() + observed_items)
        for item in items:
            new_pd[item] = curr_pd[item] * observ_pd[None]
            if item is not None:
                new_pd[item] += observ_pd[item] * 1 / p_stay


            new_pd[item] *= (1-deny_pd[item])
            if item is not deny_pd.NULL:
                new_pd[item] += (1 - deny_pd[item] * curr_pd[item] - deny_pd[deny_pd.NULL]) / (max(len(items), deny_pd.space_size - 1))

        return new_pd



class PRuleDS(IRuleDS):
    """Represents Dialogue State (DS) for Probabilistic Rule Dialogue Manager"""
    def __init__(self, user_slots):
        super(PRuleDS, self).__init__()

        # initialize user's state
        self.user_slots = user_slots
        self.inform = {}
        for slot in user_slots:
            self.inform[slot] = PDDiscrete()

        self.request = {}
        for slot in user_slots:
            self.request[slot] = PDDiscrete()

        self.meta = {}
        self.meta['reset'] = PDDiscrete()
        self.meta['alts'] = PDDiscrete()
        self.meta['bye'] = PDDiscrete()
        self.meta['alts_value'] = PDDiscrete({0: 1.0})
        self.meta['other'] = PDDiscrete()
        self.meta['hello'] = PDDiscrete()

        self.filter = {}
        for slot in user_slots:
            self.filter[slot] = PDDiscrete()


class PStateVariableTransition(object):
    state_variable = None
    dat = None

    @classmethod
    def sysaction_reaction(cls, state, last_action):
        pass

    @classmethod
    def dai_to_pd(cls, prob, dai):
        raise NotImpelementedError()

    @classmethod
    def get_update_pd(cls, prob, dai):
        return cls.dai_to_pd(prob, dai)

    @classmethod
    def update(cls, state, da_cn, last_action):
        assert isinstance(da_cn, DialogueActConfusionNetwork)

        cls.sysaction_reaction(state, last_action)

        for prob, dai in da_cn:
            # check dai for sanity
            if dai.name is None or len(dai.name) == 0:
                continue

            if dai.dat == cls.dat:
                # load
                svar = getattr(state, cls.state_variable)

                # skip over unknown slots
                if not dai.name in svar:
                    continue

                # update
                slot_pd = svar[dai.name]
                update_pd = cls.get_update_pd(prob, dai)
                new_slot_pd = SimpleSlotUpdater.update_slot(slot_pd, update_pd)

                # store
                svar[dai.name] = new_slot_pd


class PValTransition(PStateVariableTransition):
    state_variable = "inform"
    dat = "inform"

    @classmethod
    def dai_to_pd(cls, prob, dai):
        return PDDiscrete({dai.value: prob})


class PReqTransition(PStateVariableTransition):
    state_variable = "request"
    dat = "request"

    @classmethod
    def sysaction_reaction(cls, state, last_action):
        for sysaction in last_action:
            if sysaction.action == Action.Provide:
                state_update(state.request, sysaction.params['slot'], RequestSlotValue.system_provided, 1.0)


    @classmethod
    def dai_to_pd(cls, prob, dai):
        return PDDiscrete({RequestSlotValue.user_requested: prob})


def state_update(storage, key, slot_key, slot_prob):
    slot_pd = storage[key]
    storage[key] = ExtendedSlotUpdater.update_slot(slot_pd, PDDiscrete({slot_key: slot_prob}))


class PMetaTransition(object):
    other_decay_rate = 0.3

    @classmethod
    def sysaction_reaction(cls, state, last_action):
        seen_alts = False  # has the user said he wants an alternative?

        for sysaction in last_action:
            # disable hello messages if we already heloed
            if sysaction.action == Action.Hello:
                state_update(state.meta, "hello", HelloSlotValue.done, 1.0)

            # mark that we said bye
            if sysaction.action == Action.Bye:
                state_update(state.meta, "bye", ByeSlotValue.done, 1.0)

            # update alternatives counter if user asked for one
            if sysaction.action == Action.Alts:
                seen_alts = True
                state_update(state.meta, "alts", AltsSlotValue.done, 1.0)
                alts_value, _ = state.meta["alts_value"].get_max()
                new_alts_value = alts_value + 1
                state_update(state.meta, "alts_value", new_alts_value, 1.0)

            # reset misunderstanding counter if we said we did not understand
            if sysaction.action == Action.NoEntiendo:
                state_update(state.meta, "other", OtherSlotValue.done, 1.0)
            else:  # decay the misunderstanding counter otherwise
                state_update(state.meta, "other", None, cls.other_decay_rate)

            # mark that the user no longer want reset because we have just done it
            if sysaction.action == Action.Reset:
                state_update(state.meta, "reset", ResetSlotValue.done, 1.0)

            if sysaction.action == Action.ChangeFilter:
                state_update(state.meta, "reset", ResetSlotValue.done, 1.0)

        #if not seen_alts:
        #    state_update(state.meta, "alts", AltsSlotValue.done, 1.0)
        #    state_update(state.meta, "alts_value", 0, 1.0)

    @classmethod
    def update(cls, state, da_cn, last_action):
        assert isinstance(da_cn, DialogueActConfusionNetwork)

        cls.sysaction_reaction(state, last_action)

        # user input reaction
        for prob, dai in da_cn:
            if dai.dat == "reset":
                state_update(state.meta, "reset", ResetSlotValue.yes, prob)
            elif dai.dat == "other":
                state_update(state.meta, "other", OtherSlotValue.yes, prob)
            elif dai.dat == "reqalts":
                state_update(state.meta, "alts", AltsSlotValue.yes, prob)
            elif dai.dat == "bye":
                state_update(state.meta, "bye", ByeSlotValue.yes, prob)



class PConfirmTransition(object):
    @classmethod
    def update(cls, state, da_cn, last_action):
        assert isinstance(da_cn, DialogueActConfusionNetwork)

        cls.sysaction_reaction(state, last_action)

        for prob, dai in da_cn:
            if dai.dat == "confirm":
                update_pd = cls.dai_to_pd(prob, dai)
                state.confirm = SimpleSlotUpdater.update_slot(state.confirm, update_pd)

    @classmethod
    def sysaction_reaction(cls, state, last_action):
        for sysaction in last_action:
            if sysaction.action == Action.Confirm:
                update_pd = PDDiscrete({ConfirmSlotValue.done: 1.0})
                state.confirm = SimpleSlotUpdater.update_slot(state.confirm, update_pd)

    @classmethod
    def dai_to_pd(cls, prob, dai):
        return PDDiscrete({(dai.name, dai.value): prob})


class PFilterTransition(object):
    @classmethod
    def get_query(cls, state):
        query = {}
        for slot, filter_pd in state.filter.items():
            item, prob = filter_pd.get_max()
            if item is not None:
                query[slot] = item[0]  # item = (value, state)
        return query

    @classmethod
    def update(cls, state):
        query = PDbInfo.make_query(state.inform)
        curr_query = cls.get_query(state)

        # diff curr_query and query
        for slot, value in set(curr_query.items()):
            if query[slot] != value:
                state_update(state.filter, slot, (query[slot], FilterSlotValue.updated, ), 1.0)
            elif query[slot] == value:
                state_update(state.filter, slot, (query[slot], FilterSlotValue.filtering, ), 1.0)
            elif not slot in query:
                state_update(state.filter, slot, (value, FilterSlotValue.stopped_filtering, ), 1.0)

        for slot, value in query.items():
            if slot not in curr_query:
                state_update(state.filter, slot, (value, FilterSlotValue.started_filtering, ), 1.0)


        print "%" * 30
        for key, value in state.filter.items():
            print key, value
        print "%" * 30



def max_val_of(storage, key):
    return storage[key].get_max()

action_compatibility = {
    Action.Provide: (1, ),
    Action.Confirm: (1, ),
    Action.Inform: (8,),
    Action.NoMatch: (2, ),
    Action.NoEntiendo: (2, ),
    Action.Alts: (3, 8, ),
    Action.Hello: (4, ),
    Action.Bye: (5, ),
    Action.Reset: (6, ),
    Action.Instructions: (7, ),
    Action.ChangeFilter: (1, 2, 3, 8, ),
}

class PAction(object):
    @classmethod
    def get(cls, state, dbinfo_pd):
        actions = []

        # META ACTIONS
        hello_val, hello_p = max_val_of(state.meta, 'hello')
        if hello_val == None:
            actions += [(hello_p, SystemAction(Action.Hello))]

        bye_val, bye_p = max_val_of(state.meta, 'bye')
        if bye_val == ByeSlotValue.yes:
            actions += [(bye_p, SystemAction(Action.Bye))]

        reset_val, reset_p = max_val_of(state.meta, 'reset')
        if reset_val == ResetSlotValue.yes:
            actions += [(reset_p, SystemAction(Action.Reset))]

        other_val, other_p = max_val_of(state.meta, 'other')
        if other_val == OtherSlotValue.yes:
            actions += [(other_p, SystemAction(Action.NoEntiendo))]

        alts_val, alts_p = max_val_of(state.meta, 'alts')
        if alts_val == AltsSlotValue.yes:
            actions += [(alts_p, SystemAction(Action.Alts))]

        db_val, db_p = dbinfo_pd.get_max()
        if db_val is None:
            actions += [(db_p, SystemAction(Action.NoMatch))]

        # CONFIRM
        confirm_val, confirm_p = state.confirm.get_max()
        if confirm_val is not None and confirm_val != ConfirmSlotValue.done:
            actions += [(confirm_p, SystemAction(Action.Confirm, {'slot': confirm_val[0], 'value': confirm_val[1]}))]

        # REQUEST
        for slot in state.user_slots:
            req_val, req_p = max_val_of(state.request, slot)
            if req_val == RequestSlotValue.user_requested:
                actions += [(req_p, SystemAction(Action.Provide, {'slot': slot}))]

        # filter changes
        for slot in state.filter:
            filter_val, filter_p = max_val_of(state.filter, slot)

            if filter_val is not None:
                value, value_state = filter_val

                if value_state in (FilterSlotValue.started_filtering, FilterSlotValue.stopped_filtering):
                    actions += [(filter_p, SystemAction(Action.ChangeFilter, {'slot': slot, 'value': value, 'how': value_state}))]

        actions += [(0.0, SystemAction(Action.Inform))]
        actions.sort(reverse=True)

        # create groups
        agroups = defaultdict(lambda: (-1, []))
        for action_p, action in actions:
            for group in action_compatibility[action.action]:
                curr_p, curr_lst = agroups[group]
                curr_lst += [action]
                agroups[group] = (max(curr_p, action_p), curr_lst,)

        # pick the best one
        _, best_group = sorted(agroups.values(), reverse=True)[0]

        return best_group


class PDbInfo(object):
    belief_thresh = 0.5

    @classmethod
    def make_query(cls, inform):
        res = {}
        for slot, slot_pd in inform.items():
            value, prob = slot_pd.get_max()

            if value != None and prob >= cls.belief_thresh:
                res[slot] = value
        return res

    @classmethod
    def get(cls, state, db):
        inform = state.inform
        query = cls.make_query(inform)

        db_items = db.get_matching(query)
        db_items_cnt = len(db_items)

        uniform_items = {}
        for item in db_items:
            uniform_items[item['id']] = 1.0 / db_items_cnt

        res = PDDiscrete(uniform_items)
        return res


class PRuleDM(DialogueManager):
    def __init__(self, cfg, db):
        super(PRuleDM, self).__init__(cfg)

        self.state = None

        self.db = db
        self.last_action = DialogueAct()

        self.new_dialogue()

    def da_in(self, cn):
        PValTransition.update(self.state, cn, self.last_action)
        PReqTransition.update(self.state, cn, self.last_action)
        PConfirmTransition.update(self.state, cn, self.last_action)
        PMetaTransition.update(self.state, cn, self.last_action)
        PFilterTransition.update(self.state)

    def da_out(self):
        dbinfo_pd = PDbInfo.get(self.state, self.db)
        actions = PAction.get(self.state, dbinfo_pd)
        self.print_action(actions)
        self.last_action = actions

        sayer = CamInfoSayer(self.db, self.state, actions, dbinfo_pd)
        utterances = sayer.say()
        text_out = ". ".join(utterances)
        print text_out

        return DialogueAct("read(text='%s')" % text_out)

    def new_dialogue(self):
        self.state = PRuleDS(self.db.get_slots())

    def end_dialogue(self):
        pass

    def print_state(self):
        print '#' * 80
        print 'inform', self.state.inform
        print 'confirm', self.state.confirm
        print 'request', self.state.request
        print 'meta', self.state.meta
        print '-' * 80

    def print_action(self, acts):
        for act in acts:
            print " !!", act




class SimpleSayer(object):
    def get_slot_human_form(self, name):
        return name

    def get_dbentry(self):
        # alternative?
        item_number, _ = self.state.meta['alts_value'].get_max()
        if self.action_alts:
            item_number += 1

        # retrieve the correct item
        item_id, _ = self.dbinfo_pd.get_max(which_one=item_number)
        return self.db.get_by_id(item_id)

    def __init__(self, db, state, actions, dbinfo_pd):
        self.db = db
        self.state = state
        self.actions = actions

        self.action_alts = False

        self.preprocess_actions()

        # get dbentry
        self.dbinfo_pd = dbinfo_pd
        self.dbentry_item = self.get_dbentry()


    def pick_one(self, phrases):
        return random.choice(phrases)

    def preprocess_actions(self):
        """Preprocess the action_list."""
        for action in self.actions:
            if action.action == Action.Alts:
                self.action_alts = True


    def say(self):
        implicit_confirm = []
        res = []
        for action in self.actions:
            if action.action == Action.Bye:
                res += self.do_bye()
            elif action.action == Action.Hello:
                res += self.do_hello()
            elif action.action == Action.Reset:
                res += self.do_reset()
            elif action.action == Action.NoEntiendo:
                res += self.do_noentiendo()
            elif action.action == Action.Instructions:
                res += self.do_instructions()
            elif action.action == Action.Alts:
                res += self.do_alts()
            elif action.action == Action.Confirm:
                res += self.do_confirm(action.params)
            elif action.action == Action.Provide:
                implicit_confirm += self.do_pre_provide(action.params)
                res += self.do_provide(action.params)
            elif action.action == Action.Inform:
                res += self.do_inform()
            elif action.action == Action.NoMatch:
                res += self.do_nomatch()
            elif action.action == Action.ChangeFilter:
                implicit_confirm += self.do_filterchange(action.params)

        if len(implicit_confirm) > 0:
            res = ["Okay, %s" % " and ".join(implicit_confirm)] + res

        return res

    def do_hello(self):
        return ["Hi! How may I help you?"]

    def do_bye(self):
        return ["Bye bye, call again!"]

    def do_reset(self):
        return ["Okay, reset. I've just cleaned my filters."]

    def do_noentiendo(self):
        return [self.pick_one([
                    "My hearing is bad, can you say it more clearly?",
                    "Sorry, I didn't understand you.",
                    "Please, say that again."])]

    def do_instructions(self):
        return [self.instructions_text]

    def do_alts(self):
        return ["Okay, you want another one."]

    def do_confirm(self, params):
        res = []
        if params['slot'] in self.dbentry_item:
            if self.dbentry_item[params['slot']] == params['value']:
                res += ["Yes, %s." % self.say_slot(params['slot'], params['value'])]
            else:
                res += ["No, I am afraid that %s is not %s" % (params['slot'], params['value']),
                         self.say_slot(params['slot'], self.dbentry_item[params['slot']]),
                ]

        else:
            res += ["Sorry I have no clue about %s of this item." % self.get_slot_human_form(params['slot'])]

        return res

    def do_pre_provide(self, params):
        res = ["you want to know the %s" % self.get_slot_human_form(params['slot'])]
        return res

    def do_provide(self, params):
        res = []  # "Okay, you want to know the %s." % self.get_slot_human_form(params['slot'])]
        if params['slot'] in self.dbentry_item:
            res += ["%s" % self.say_slot(params['slot'], self.dbentry_item[params['slot']])]
        return res


    def do_inform(self):
        res = ["Here is the information."]
        keys = ["name", "area"]

        for key in keys:
            res += ["%s" % self.say_slot(key, self.dbentry_item[key])]
        return res

    def do_nomatch(self):
        query = PDbInfo.make_query(self.state.inform)
        res = ["Sorry, our database does not contain anything that is matching your criterions."]
        for key, value in query.items():
            res += ["you want %s" % self.say_want(key, value)]
        return res

    def do_filterchange(self, params):
        if params['how'] == FilterSlotValue.started_filtering:
            how_text = "you want"
        elif params['how'] == FilterSlotValue.stopped_filtering:
            how_text = "you no longer want"

        res = "%s %s" % (how_text, self.say_want(params['slot'], params['value']), )
        return [res]

    def say_want(self, name, value):
        raise NotImpelementedError()

    def say_slot(self, name, value):
        raise NotImpelementedError()



class CamInfoSayer(SimpleSayer):
    instructions_text = "I can give you information about restaurants in Cambridge."

    def say_slot(self, name, value):
        if name == "food":
            res = "it serves %s food" % value
        elif name == "name":
            res = "the place is called %s" % value
        elif name == "pricerange":
            res = "the prices are %s" % value
        elif name == "price":
            res = value
        elif name == "area":
            res = "it is located in the %s area" % value
        elif name == "addr":
            res = "address of the place is %s" % value
        elif name == "phone":
            res = "its phone number is %s" % value
        else:
            res = "its attribute %s is %s" % (name, value,)
        return res

    def say_want(self, name, value):
        if name == "food":
            res = "it to serve %s food" % value
        elif name == "name":
            res = "a place called %s" % value
        elif name == "pricerange":
            res = "%s pricerange" % value
        elif name == "area":
            res = "something in the %s area" % value
        else:
            res = "the attribute %s to be %s" % (name, value,)
        return res


def main():
    from alex.utils.config import Config
    from alex.utils.caminfodb import CamInfoDb


    cfg = Config('resources/default.cfg', project_root=True)
    cfg.merge('resources/lz.cfg', project_root=True)

    db_cfg = cfg['DM']["PUfalRuleDM"]['db_cfg']  # database provider
    db = CamInfoDb(db_cfg)

    pdm = PRuleDM(cfg, db)
    pdm.new_dialogue()
    pdm.da_out()

    # user's input
    cn = DialogueActConfusionNetwork()
    cn.add(0.7, DialogueActItem(dai="inform(food=chinese)"))
    cn.add(0.2, DialogueActItem(dai="inform(food=indian)"))
    cn.add(0.5, DialogueActItem(dai="inform(food=chinese)"))
    cn.add(0.1, DialogueActItem(dai="inform(food=czech)"))
    cn.add(0.1, DialogueActItem(dai="confirm(food=czech)"))
    cn.add(0.6, DialogueActItem(dai="request(phone)"))
    cn.add(0.3, DialogueActItem(dai="reset()"))
    cn.add(0.3, DialogueActItem(dai="asdf()"))
    cn.add(0.3, DialogueActItem(dai="reset()"))
    print cn
    pdm.da_in(cn)
    pdm.da_out()

    cn = DialogueActConfusionNetwork()
    cn.add(0.99, DialogueActItem(dai="confirm(food=indian)"))
    print cn
    pdm.da_in(cn)
    pdm.da_out()

    cn = DialogueActConfusionNetwork()
    cn.add(0.77, DialogueActItem(dai="reqalts()"))
    print cn
    pdm.da_in(cn)
    pdm.da_out()

    cn = DialogueActConfusionNetwork()
    cn.add(0.77, DialogueActItem(dai="reqalts()"))
    print cn
    pdm.da_in(cn)
    pdm.da_out()

    cn = DialogueActConfusionNetwork()
    cn.add(0.99, DialogueActItem(dai="confirm(food=indian)"))
    print cn
    pdm.da_in(cn)
    pdm.da_out()

    cn = DialogueActConfusionNetwork()
    cn.add(0.99, DialogueActItem(dai="request(name)"))
    cn.add(0.99, DialogueActItem(dai="request(food)"))
    print cn
    pdm.da_in(cn)
    pdm.da_out()

    cn = DialogueActConfusionNetwork()
    cn.add(0.99, DialogueActItem(dai="bye()"))
    print cn
    pdm.da_in(cn)
    pdm.da_out()


    #dm = PRuleDM(cfg)
    #dm.da_in()

if __name__ == '__main__':
    main()


