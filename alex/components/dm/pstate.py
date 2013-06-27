
class PDDiscreteBase(object):
    def __init__(self, *args, **kwargs):
        self._sorted = None

    def get_best(self):
        return sorted(self.distrib.items(), key=lambda x: -x[1])

    def get_max(self, which_one=0):
        res = sorted(self.distrib.items(), key=lambda x: -x[1])
        return res[which_one]

    def remove(self, item):
        del self.distrib[item]

    def __len__(self):
        return len(self.distrib)


class PDDiscrete(PDDiscreteBase):
    """Discrete probability distribution."""
    NULL = None
    OTHER = "<other>"

    meta_slots = set([NULL, OTHER])

    def __init__(self, initial=None):
        super(PDDiscrete, self).__init__()

        self._entropy = None

        if initial is None:
            self.distrib = {None: 1.0}
        else:
            self.distrib = initial
            if not None in self.distrib:
                self.distrib[None] = max(0.0, 1.0 - sum(self.distrib.values()))

    def update(self, items):
        self._entropy = None
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

    def get_distrib(self):
        return self.distrib.items()

    def iteritems(self):
        return self.distrib.iteritems()



    def get_entropy(self):
        if self._entropy is None:
            self._entropy = common.entropy(self)

        return self._entropy

    def normalize(self):
        """Normalize the probability distribution."""
        total_sum = sum(self.distrib.values())
        self._entropy = None

        if total_sum == 0:
            raise NotNormalisedError()  

        for key in self.distrib:
            self[key] /= total_sum

    def __getitem__(self, key):
        if key in self.distrib:
            return self.distrib[key]
        else:
            return 0.0

    def __setitem__(self, key, value):
        self._entropy = None
        self.distrib[key] = value

    def __repr__(self):
        return "<%s>" % " | ".join(["%s: %.2f" % (key, value, )
                            for key, value
                            in sorted(self.distrib.items(), key=lambda x: -x[1])])


class PDDiscreteOther(PDDiscreteBase):
    """Discrete probability distribution with sink probability slot for OTHER."""
    NULL = None
    OTHER = "<other>"

    space_size = None
    meta_slots = set([NULL, OTHER])

    def __init__(self, space_size, initial=None):
        super(PDDiscreteOther, self).__init__()

        self.space_size = space_size
        self._entropy = None

        if initial is None:
            self.distrib = {self.NULL: 1.0, self.OTHER: 0.0}
        else:
            self.distrib = initial
            if not self.NULL in self.distrib:
                self.distrib[self.NULL] = max(0.0, 1.0 - sum(self.distrib.values()))

    def update(self, items):
        self._entropy = None
        none_mass = max(1.0 - sum(items.values()), 0.0)
        self.distrib = {}
        self.distrib[self.OTHER] = 0.0
        for item, mass in items.items():
            self.distrib[item] = mass

        if not self.NULL in items:
            self.distrib[self.NULL] += none_mass

    def get(self, item):
        if item in self.distrib:
            return self.distrib[item]
        else:
            remaining_space_size = (self.space_size - len(self.distrib) - 2)
            if remaining_space_size > 0:
                return self.distrib.get(self.OTHER, 0.0) / remaining_space_size
            else:
                return 0.0

    def iteritems(self):
        return self.distrib.iteritems()

    def get_items(self):
        return self.distrib.keys()

    def get_distrib(self):
        return self.distrib.items()

    def get_max(self, which_one=0):
        res = sorted(self.distrib.items(), key=lambda x: -x[1])
        return res[which_one]

    def get_entropy(self):
        if self._entropy is None:
            self._entropy = common.entropy(self)

        return self._entropy

    def normalize(self, redistrib=0.0):
        """Normalize the probability distribution."""
        self._entropy = None
        total_sum = sum(self.distrib.values())

        if total_sum == 0:
            total_sum = 1.0
            if len(self.distrib) > 1 and redistrib == 0.0:
                raise NotNormalisedError()  
            elif redistrib > 0.0:
                for key in self.distrib.keys():
                    self[key] += redistrib / len(self.distrib)
            else:
                if len(self.distrib) == 0:
                    self[None] = 1.0
                else:
                    self[self.distrib.keys()[0]] = 1.0

        for key in self.distrib:
            self[key] /= total_sum

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self._entropy = None
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
