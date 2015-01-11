#!/usr/bin/env python
# encoding: utf8

"""
.. module:: dstc_tracker
    :synopsis: Discriminative tracker that was used for DSTC2012.

.. moduleauthor:: Lukas Zilka <lukas@zilka.me>
"""
if __name__ == '__main__':
    import autopath

from collections import defaultdict

from alex.components.dm.pstate import PDDiscrete, PDDiscreteOther
from alex.components.dm.tracker import StateTracker
from alex.components.slu.da import DialogueActConfusionNetwork, DialogueActItem

NOTHING_DENIED = "@N@"
NO_VALUE = None

class DSTCState(object):
    """Represents state of the tracker."""
    def __init__(self, slots):
        """Initialise state that has given slots.

        Arguments:
            - slots: list of slot names (strings)"""
        self.slots = slots

        # each slot is a distribution over its values
        self.values = {}
        for slot in slots:
            self.values[slot] = PDDiscrete()

    def __getitem__(self, item):
        """Get distribution for given slot."""
        return self.values[item]

    def __setitem__(self, item, value):
        """Set distribution for given slot."""
        self.values[item] = value

    def pprint(self):
        """Pretty-print self."""
        res = []
        for slot in self.slots:
            val = ' |%s| ' % slot
            val += str(self.values[slot])
            res.append(val)
        return "\n".join(res)

    def __str__(self):
        return self.pprint()


class ExtendedSlotUpdater(object):
    """Updater of state given observation and deny distributions."""
    @classmethod
    def update_slot(cls, curr_pd, observ_pd, deny_pd):
        new_pd = PDDiscrete()  # initialize result

        # find out which items need to be computed
        observed_items = observ_pd.get_items()
        observed_items += deny_pd.get_items()

        items = set(curr_pd.get_items() + observed_items)
        for item in items:
            # compute probability of item according to the formula:
            # p_{t}(item) = (p_{t-1}(item)*p(None) + p(item)) * (1-p_deny(item)) +
            #               + (1-p_deny(item)*p(item)-p_deny(nothing_denied)) / N
            # where N is the total number of items in the distribution (note that this
            # is usually not equal to items actually represented in the distribution,
            # as we do not explicitely represent items that we have not seen)
            new_pd[item] = curr_pd[item] * observ_pd[NO_VALUE]
            if item is not NO_VALUE:
                new_pd[item] += observ_pd[item]

            new_pd[item] *= (1-deny_pd[item])
            if item is not NOTHING_DENIED:
                new_pd[item] += (1 - deny_pd[item] * curr_pd[item] - deny_pd[NOTHING_DENIED]) / (max(len(items), deny_pd.space_size - 1))

        return new_pd


class DSTCTracker(StateTracker):
    """Represents simple deterministic DSTC state tracker."""
    state_class = DSTCState

    def __init__(self, slots, default_space_size=defaultdict(lambda: 100)):
        super(DSTCTracker, self).__init__()

        self.slots = slots
        self.default_space_size = default_space_size

        self.values = {}
        for slot in slots:
            self.values[slot] = PDDiscrete()

    def update_state(self, state, cn):
        # initialize distributions used for computing distributions from the confusion network
        inform_slot_distr = defaultdict(PDDiscrete)
        deny_slot_distr = defaultdict(PDDiscreteOther)
        for slot in self.slots:
            inform_slot_distr[slot] = PDDiscrete()
            deny_slot_distr[slot] = PDDiscreteOther(space_size=self.default_space_size[slot])
            deny_slot_distr[slot][NO_VALUE] = 0.0
            deny_slot_distr[slot][NOTHING_DENIED] = 1.0

        # go through confusion network and add-up probabilities into the inform and deny
        # distributions (they as if represent scores for particular items; we normalize
        # afterwards)
        sum_inform = defaultdict(float)
        sum_deny = defaultdict(float)
        for p, dai in cn:
            if dai.dat == "inform":
                inform_slot_distr[dai.name][dai.value] = p
                sum_inform[dai.name] += p
            elif dai.dat == "deny":
                deny_slot_distr[dai.name][dai.value] = p
                sum_deny[dai.name] += p

        # update each slot independently according to the distributions from conf.net.
        for slot in state.slots:
            inform_slot_distr[slot][NO_VALUE] = max(0.0, 1 - sum_inform[slot])
            inform_slot_distr[slot].normalize()

            deny_slot_distr[slot][NOTHING_DENIED] = max(0.0, 1 - sum_deny[slot])
            deny_slot_distr[slot].normalize()

            state[slot] = ExtendedSlotUpdater.update_slot(state[slot], inform_slot_distr[slot], deny_slot_distr[slot])


def main():

    # initialize tracker and state
    slots = ["food", "location"]
    tr = DSTCTracker(slots)
    state = DSTCState(slots)
    state.pprint()

    # try to update state with some information
    print '---'
    cn = DialogueActConfusionNetwork()
    cn.add(0.3, DialogueActItem("inform", "food", "chinese"))
    cn.add(0.1, DialogueActItem("inform", "food", "indian"))
    tr.update_state(state, cn)
    state.pprint()

    # try to deny some information
    print '---'
    cn.add(0.9, DialogueActItem("deny", "food", "chinese"))
    cn.add(0.1, DialogueActItem("deny", "food", "indian"))
    tr.update_state(state, cn)
    state.pprint()



if __name__ == '__main__':
    main()



