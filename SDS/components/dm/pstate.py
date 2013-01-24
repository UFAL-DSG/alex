
class PDDiscrete(object):
    def __init__(self, initial=None):
        if initial is None:
            self.distrib = {None: 1.0}
        else:
            self.distrib = initial
            if not None in self.distrib:
                self.distrib[None] = max(0.0, 1.0 - sum(self.distrib.values()))

    def update(self, items):
        none_mass = max(1.0 - sum(items.values()), 0.0)
        self.distrib = {}
        self.distrib[None] = none_mass
        for item, mass in items.items():
            self.distrib[item] = mass

    def get(self, item):
        if item in self.distrib:
            return self.distrib[item]
        else:
            return 0.0

    def get_items(self):
        return self.distrib.keys()

    def get_max(self, which_one=0):
        res = sorted(self.distrib.items(), key=lambda x: -x[1])
        return res[which_one]

    def __getitem__(self, key):
        if key in self.distrib:
            return self.distrib[key]
        else:
            return 0.0

    def __setitem__(self, key, value):
        self.distrib[key] = value

    def __repr__(self):
        return "<%s>" % " | ".join(["%s: %.2f" % (key, value, )
                            for key, value
                            in sorted(self.distrib.items(), key=lambda x: -x[1])])


class SimpleUpdater(object):
    def __init__(self, slots):
        self.slots = {}
        for slot in slots:
            self.slots[slot] = PDDiscrete()

    def update(self, observ):
        for slot, observ_distrib in observ.items():
            self.update_slot(slot, observ_distrib)

    def update_slot(self, slot, observ_distrib):
        observed_items = observ_distrib.get_items()

        new_pd = PDDiscrete()
        curr_pd = self.slots[slot]

        items = set(curr_pd.get_items() + observed_items)

        for item in items:
            new_pd[item] = curr_pd[item] * observ_distrib[None]
            if item is not None:
                new_pd[item] += observ_distrib[item]

        self.slots[slot] = new_pd

    def __repr__(self):
        return "\n".join("%s: %s" % (key, str(pd), ) for key, pd in self.slots.items())


if __name__ == '__main__':
    pds = PState(["venue"])
    pds.update({'venue': PDDiscrete({"hotel": 0.5, None: 0.5})})
    pds.update({'venue': PDDiscrete({"bar": 0.5, None: 0.5})})
    pds.update({'venue': PDDiscrete({"hotel": 0.5, None: 0.5})})
    pds.update({'venue': PDDiscrete({"hotel": 0.5, None: 0.5})})
    print pds