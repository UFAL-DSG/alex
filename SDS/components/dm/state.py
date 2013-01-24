class State(object):
    def __init__(self, slots):
        self.state = {}
        for slot in slots:
            self.state[slot] = None

    def update(self, item, value):
        assert item in self.state

        state_item = self.state[item]
        if type(state_item) is list:
            state_item.extend(value)
        else:
            self.state[item] = value

    def __setitem__(self, key, value):
        self.state[key] = value

    def __getitem__(self, key):
        return self.state[key]
