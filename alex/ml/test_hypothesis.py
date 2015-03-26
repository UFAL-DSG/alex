from unittest import TestCase

from alex.ml.hypothesis import ConfusionNetwork

class TestConfusionNetwork(TestCase):
    def test_iter(self):
        dacn = ConfusionNetwork()
        dacn.add(0.2, 1)
        dacn.add(0.7, 2)
        dacn.add(0.1, 3)

        lst = list(dacn)
        self.assertTrue(lst[0][0] == 0.2)
        self.assertTrue(lst[0][1] == 1)

        self.assertTrue(lst[1][0] == 0.7)
        self.assertTrue(lst[1][1] == 2)

        self.assertTrue(lst[2][0] == 0.1)
        self.assertTrue(lst[2][1] == 3)

    def test_remove(self):
        dacn = ConfusionNetwork()
        dacn.add(0.2, 1)
        dacn.add(0.7, 2)
        dacn.add(0.1, 3)

        dacn.remove(1)
        dacn.remove(3)

        self.assertTrue(2 in dacn)
        self.assertTrue(len(dacn) == 1)