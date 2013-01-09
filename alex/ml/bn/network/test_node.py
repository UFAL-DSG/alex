#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=C0111

import unittest
import pdb

from bn.factor import DiscreteFactor
from bn.network.node import DiscreteVariableNode, DiscreteFactorNode

class TestNode(unittest.TestCase):

    def assertClose(self, first, second, epsilon=0.000001):
        delta = abs(first - second)
        self.assertLess(delta, epsilon)

    def test_network(self):
        # Create network.
        hid = DiscreteVariableNode("hid", ["save", "del"])
        obs = DiscreteVariableNode("obs", ["osave", "odel"])
        fact_h1_o1 = DiscreteFactorNode("fact_h1_o1", DiscreteFactor(
            {
                "hid": ["save", "del"],
                "obs": ["osave", "odel"]
            },
            {
                ("save", "osave"): 0.3,
                ("save", "odel"): 0.6,
                ("del", "osave"): 0.7,
                ("del", "odel"): 0.4
            }))

        # Add edges.
        obs.add_edge_to(fact_h1_o1)
        fact_h1_o1.add_edge_to(hid)

        # Init messages.
        hid.init_messages()
        obs.init_messages()
        fact_h1_o1.init_messages()

        # 1. Without observations, send_messages used.
        obs.send_messages()
        fact_h1_o1.send_messages()

        hid.update_belief()
        hid.normalize()
        self.assertClose(hid.belief[("save",)], 0.45)

        # 2. Observed value, message_to and update_belief used.
        obs.observed("osave")
        obs.message_to(fact_h1_o1)
        fact_h1_o1.update_belief()
        fact_h1_o1.message_to(hid)
        hid.update_belief()

        hid.normalize()
        self.assertClose(hid.belief[("save",)], 0.3)

        # 3. Without observations, send_messages used.
        obs.observed(None)
        obs.send_messages()
        fact_h1_o1.send_messages()

        hid.update_belief()
        hid.normalize()
        self.assertClose(hid.belief[("save",)], 0.45)