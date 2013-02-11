class IRuleDS(object):
    USER_DA = "user"
    SYSTEM_DA = "system"

    def update_user(self, what, certainty):
        raise NotImplementedError()

    def update_user_request(self, what, certainty):
        raise NotImplementedError()

    def update_user_confirm(self, what, certainty):
        raise NotImplementedError()

    def update_user_alternative(self):
        raise NotImplementedError()

    def get_user_alternative(self):
        raise NotImplementedError()

    def update_system(self, what):
        raise NotImplementedError()

    def new_turn(self):
        raise NotImplementedError()

    def new_da(self, da, who):
        raise NotImplementedError()

    def get_curr_user_da(self):
        raise NotImplementedError()

    def clear(self):
        raise NotImplementedError()


class RuleDS(IRuleDS):
    def __init__(self):
        super(RuleDS, self).__init__()
        self.da_history = []

    def clear(self):
        self.da_history = []

    def new_da(self, da, who='user'):
        self.da_history += [{'da': da, 'actor': who}]

    def get_curr_user_da(self):
        for da in reversed(self.da_history):
            if da['actor'] == IRuleDS.USER_DA:
                return da['da']

        return None
