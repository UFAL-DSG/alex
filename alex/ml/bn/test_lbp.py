#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from bn.factor import DiscreteFactor
from bn.node import DiscreteVariableNode, DiscreteFactorNode
from bn.lbp import LBP

class TestLBP(unittest.TestCase):

    def test_network(self):
        # Create nodes.
        hid1 = DiscreteVariableNode("hid1", ["save", "del"])
        obs1 = DiscreteVariableNode("obs1", ["osave", "odel"])
        fact_h1_o1 = DiscreteFactorNode("fact_h1_o1", DiscreteFactor(
            ['hid1', 'obs1'],
            {
                "hid1": ["save", "del"],
                "obs1": ["osave", "odel"]
            },
            {
                ("save", "osave"): 0.8,
                ("save", "odel"): 0.3,
                ("del", "osave"): 0.2,
                ("del", "odel"): 0.7,
            }))

        hid2 = DiscreteVariableNode("hid2", ["save", "del"])
        obs2 = DiscreteVariableNode("obs2", ["osave", "odel"])
        fact_h2_o2 = DiscreteFactorNode("fact_h2_o2", DiscreteFactor(
            ['hid2', 'obs2'],
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
            ['hid1', 'hid2'],
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

        obs1.observed({('osave',):1})
        lbp.run(1)
        hid1.normalize()
        print hid1.belief

        obs2.observed({('odel',):1})
        lbp.run(1)
        hid1.normalize()
        print hid1.belief

    def test_single_linked(self):
        f_h_o = {
            ("save", "osave"): 0.8,
            ("save", "odel"): 0.3,
            ("del", "osave"): 0.2,
            ("del", "odel"): 0.7,
        }

        f_h_h = {
            ("save", "save"): 0.9,
            ("save", "del"): 0.1,
            ("del", "save"): 0.1,
            ("del", "del"): 0.9
        }
        # Create nodes.
        hid1 = DiscreteVariableNode("hid1", ["save", "del"])
        obs1 = DiscreteVariableNode("obs1", ["osave", "odel"])
        fact_h1_o1 = DiscreteFactorNode("fact_h1_o1", DiscreteFactor(
            ['hid1', 'obs1'],
            {
                "hid1": ["save", "del"],
                "obs1": ["osave", "odel"]
            },
            f_h_o))

        hid2 = DiscreteVariableNode("hid2", ["save", "del"])
        obs2 = DiscreteVariableNode("obs2", ["osave", "odel"])
        fact_h2_o2 = DiscreteFactorNode("fact_h2_o2", DiscreteFactor(
            ['hid2', 'obs2'],
            {
                "hid2": ["save", "del"],
                "obs2": ["osave", "odel"]
            },
            f_h_o))

        fact_h1_h2 = DiscreteFactorNode("fact_h1_h2", DiscreteFactor(
            ['hid1', 'hid2'],
            {
                "hid1": ["save", "del"],
                "hid2": ["save", "del"],
            },
            f_h_h))

        hid3 = DiscreteVariableNode("hid3", ["save", "del"])
        obs3 = DiscreteVariableNode("obs3", ["osave", "odel"])
        fact_h3_o3 = DiscreteFactorNode("fact_h3_o3", DiscreteFactor(
            ['hid3', 'obs3'],
            {
                "hid3": ["save", "del"],
                "obs3": ["osave", "odel"]
            },
            f_h_o))

        fact_h2_h3 = DiscreteFactorNode("fact_h2_h3", DiscreteFactor(
            ['hid2', 'hid3'],
            {
                "hid2": ["save", "del"],
                "hid3": ["save", "del"],
            },
            f_h_h))

        # Connect nodes.
        obs1.add_edge_to(fact_h1_o1)
        obs2.add_edge_to(fact_h2_o2)
        obs3.add_edge_to(fact_h3_o3)

        fact_h1_o1.add_edge_to(hid1)
        fact_h2_o2.add_edge_to(hid2)
        fact_h3_o3.add_edge_to(hid3)

        hid1.add_edge_to(fact_h1_h2)
        hid2.add_edge_to(fact_h1_h2)

        hid2.add_edge_to(fact_h2_h3)
        hid3.add_edge_to(fact_h2_h3)

        # Add nodes to lbp.
        lbp = LBP(strategy='tree')
        lbp.add_nodes([
            obs1, obs2, obs3,
            fact_h1_o1, fact_h2_o2, fact_h3_o3,
            hid1, hid2, hid3,
            fact_h1_h2, fact_h2_h3
        ])

        print "RUN"
        lbp.run()
