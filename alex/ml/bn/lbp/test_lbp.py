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
        obs1.add_edge_to(fact_h1_o1)
        fact_h1_o1.add_edge_to(hid1)

        obs2.add_edge_to(fact_h2_o2)
        fact_h2_o2.add_edge_to(hid2)

        hid1.add_edge_to(fact_h1_h2)
        hid2.add_edge_to(fact_h1_h2)

        # Add nodes to lbp.
        lbp = LBP()
        lbp.add_nodes([
            obs1, fact_h1_o1, hid1,
            obs2, fact_h2_o2, hid2,
            fact_h1_h2
        ])

        lbp.run(1)

        print hid1.belief

        obs1.observed('osave')
        lbp.run(1)
        print hid1.belief

        obs2.observed('odel')
        lbp.run(1)
        print hid1.belief
