from collections import defaultdict

import autopath
from alex.components.dm.pstate import PDDiscrete, PDDiscreteOther
from alex.components.dm.tracker import StateTracker
from alex.components.slu.da import DialogueActConfusionNetwork, DialogueActItem

class DSTCState(object):
    def __init__(self, slots):
        self.slots = slots

        self.values = {}
        for slot in slots:
            self.values[slot] = PDDiscrete()

    def __getitem__(self, item):
        return self.values[item]

    def __setitem__(self, item, value):
        self.values[item] = value

    def pprint(self):
        for slot in self.slots:
            print ' |%s| ' % slot,
            print self.values[slot]


class ExtendedSlotUpdater(object):
    @classmethod
    def update_slot(cls, curr_pd, observ_pd, deny_pd):
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


class DSTCTracker(StateTracker):
    state_class = DSTCState

    def __init__(self, slots, default_space_size=defaultdict(lambda: 100)):
        super(DSTCTracker, self).__init__()

        self.slots = slots
        self.default_space_size = default_space_size

        self.values = {}
        for slot in slots:
            self.values[slot] = PDDiscrete()

    def update_state(self, state, cn):
        inform_slot_distr = defaultdict(PDDiscrete)
        deny_slot_distr = defaultdict(PDDiscreteOther)
        for slot in self.slots:
            inform_slot_distr[slot] = PDDiscrete()
            deny_slot_distr[slot] = PDDiscreteOther(space_size=self.default_space_size[slot])

        sum_inform = 0.0
        sum_deny = 0.0
        for p, dai in cn:
            if dai.dat == "inform":
                inform_slot_distr[dai.name][dai.value] = p
                sum_inform += p
            elif dai.dat == "deny":
                deny_slot_distr[dai.name][dai.value] = p
                sum_deny += p

        # update each slot independently
        for slot in state.slots:
            inform_slot_distr[slot][None] = max(0.0, 1 - sum_inform)
            inform_slot_distr[slot].normalize()
            deny_slot_distr[slot][None] = max(0.0, 1 - sum_deny)
            deny_slot_distr[slot].normalize()

            print inform_slot_distr[slot]

            state[slot] = ExtendedSlotUpdater.update_slot(state[slot], inform_slot_distr[slot], deny_slot_distr[slot])


def main():
    slots = ["food", "location"]
    tr = DSTCTracker(slots)
    state = DSTCState(slots)
    state.pprint()
    print '---'
    cn = DialogueActConfusionNetwork()
    cn.add(0.3, DialogueActItem("inform", "food", "chinese"))
    cn.add(0.1, DialogueActItem("inform", "food", "indian"))
    tr.update_state(state, cn)
    state.pprint()

    print '---'

    cn.add(0.9, DialogueActItem("deny", "food", "chinese"))
    cn.add(0.1, DialogueActItem("deny", "food", "indian"))
    tr.update_state(state, cn)
    state.pprint()



if __name__ == '__main__':
    main()



