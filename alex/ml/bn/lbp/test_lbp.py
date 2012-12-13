#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from bn.factor import DiscreteFactor
from bn.network.node import DiscreteVariableNode, DiscreteFactorNode
from bn.lbp import LBP

class TestLBP(unittest.TestCase):

    def test_network(self):
        # Create nodes.
        hid1 = DiscreteVariableNode("hid1", ["save", "del"])
        obs1 = DiscreteVariableNode("obs1", ["osave", "odel"])
        fact_h1_o1 = DiscreteFactorNode("fact_h1_o1", DiscreteFactor(
            {
                "hid1": ["save", "del"],
                "obs1": ["osave", "odel"]
            },
            {
                ("save", "osave"): 0.8,
                ("save", "odel"): 0.2,
                ("del", "osave"): 0.3,
                ("del", "odel"): 0.7,
            }))

        hid2 = DiscreteVariableNode("hid2", ["save", "del"])
        obs2 = DiscreteVariableNode("obs2", ["osave", "odel"])
        fact_h2_o2 = DiscreteFactorNode("fact_h2_o2", DiscreteFactor(
            {
                "hid2": ["save", "del"],
                "obs2": ["osave", "odel"]
            },
            {
                ("save", "osave"): 0.8,
                ("save", "odel"): 0.2,
                ("del", "osave"): 0.2,
                ("del", "odel"): 0.8,
            }))

        fact_h1_h2 = DiscreteFactorNode("fact_h1_h2", DiscreteFactor(
            {
                "hid1": ["save", "del"],
                "hid2": ["save", "del"],
            },
            {
                ("save", "save"): 0.9,
                ("save", "del"): 0.1,
                ("del", "save"): 0,
                ("del", "del"): 1
            }))

        # Connect nodes.
        fact_h1_o1.add_neighbor(hid1)
        fact_h1_o1.add_neighbor(obs1)

        fact_h2_o2.add_neighbor(hid2)
        fact_h2_o2.add_neighbor(obs2)

        fact_h1_h2.add_neighbor(hid1)
        fact_h1_h2.add_neighbor(hid2)

        # Init nodes.
        fact_h1_o1.init_messages()
        fact_h2_o2.init_messages()
        fact_h1_h2.init_messages()
        hid1.update_belief()
        hid2.update_belief()
        obs1.update_belief()
        obs2.update_belief()

        # Add nodes to lbp.
        lbp = LBP()
        lbp.add_nodes([
            obs1, hid1, fact_h1_o1,
            obs2, hid2, fact_h2_o2,
            fact_h1_h2
        ])

        lbp.run(2)

        print hid1.belief

        obs1.observed('osave')
        lbp.run(2)
        print hid1.belief

        obs2.observed('odel')
        lbp.run(2)
        print hid1.belief
