import unittest

if __name__ == "__main__":
    import autopath
from SDS.components.dm.ruledm import RuleDM, RuleDMPolicy, UserTransformationRule


class TestInfoDb(object):
    def __init__(self, *args, **kwargs):
        self.data = {
            '0': {
                'name': '1',
                'address': 'somewhere',
            },
            '1': {
                'name': '2',
                'address': 'somewhere else',
            },
        }

    def matches(self, rec, query):
        for key, value in query.items():
            if not rec.get(key) == value:
                return False

        return True

    def get_matching(self, query):
        res = []
        for rec in self.data:
            if self.matches(rec, query):
                res += [rec]

        return res

class TestingRuleDMPolicy(RuleDMPolicy):
    db_cls = TestInfoDb

class TestingRuleDM(RuleDM):
    policy_cls = TestingRuleDMPolicy


class TestRuleDM(unittest.TestCase):
    def test_transformationrule(self):
        r1 = UserTransformationRule(
            da="affirm",
            last_da="confirm",
            t=lambda da, last_da: "inform({0}={1})".format(da.name, da.value)
        )

        r2 = UserTransformationRule(
            da="inform",
            cond=lambda da, last_da, state: da.value == "dontcare",
            t=lambda da, last_da: "dontcare()"
        )


