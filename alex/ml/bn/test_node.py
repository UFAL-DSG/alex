#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=C0111

import unittest
import pdb

from bn.factor import DiscreteFactor
from bn.node import DiscreteVariableNode, DiscreteFactorNode, DiscreteConvertedFactorNode

def same_or_different(assignment):
    return (all(assignment[0] == x for x in assignment),)

class TestNode(unittest.TestCase):

    def assertClose(self, first, second, epsilon=0.000001):
        delta = abs(first - second)
        self.assertLess(delta, epsilon)

    def test_network(self):
        # Create network.
        hid = DiscreteVariableNode("hid", ["save", "del"])
        obs = DiscreteVariableNode("obs", ["osave", "odel"])
        fact_h1_o1 = DiscreteFactorNode("fact_h1_o1", DiscreteFactor(
            ['hid', 'obs'],
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

        hid.update()
        hid.normalize()
        self.assertClose(hid.belief[("save",)], 0.45)

        # 2. Observed value, message_to and update_belief used.
        obs.observed({("osave",): 1})
        obs.message_to(fact_h1_o1)
        fact_h1_o1.update()
        fact_h1_o1.message_to(hid)
        hid.update()

        hid.normalize()
        self.assertClose(hid.belief[("save",)], 0.3)

        # 3. Without observations, send_messages used.
        obs.observed(None)
        obs.send_messages()
        fact_h1_o1.send_messages()

        hid.update()
        hid.normalize()
        self.assertClose(hid.belief[("save",)], 0.45)

    def test_function_node(self):
        s1 = DiscreteVariableNode('s1', ['a', 'b'])
        s2 = DiscreteVariableNode('s2', ['a', 'b'])
        same = DiscreteConvertedFactorNode('f', DiscreteFactor(
            ['same'],
            {
                'same': [True, False]
            },
            {
                (True,): 0.8,
                (False,): 0.2
            }),
            same_or_different)

        s1.add_edge_to(same)
        s2.add_edge_to(same)

        s1.init_messages()
        s2.init_messages()
        same.init_messages()

        s2.observed({('a',):1})

        s1.send_messages()
        s2.send_messages()

        same.update()
        same.normalize()

        same.send_messages()

        s1.update()
        s1.normalize()

        self.assertClose(s1.belief[('a',)], 0.8)
        self.assertClose(s1.belief[('b',)], 0.2)
        self.assertClose(s2.belief[('a',)], 1)

    def test_observed_complex(self):
        s1 = DiscreteVariableNode('s1', ['a', 'b'])
        s2 = DiscreteVariableNode('s2', ['a', 'b'])
        f = DiscreteFactorNode('f', DiscreteFactor(
            ['s1', 's2'],
            {
                's1': ['a', 'b'],
                's2': ['a', 'b'],
            },
            {
                ('a', 'a'): 1,
                ('a', 'b'): 0.5,
                ('b', 'a'): 0,
                ('b', 'b'): 0.5
            }))

        s1.add_edge_to(f)
        s2.add_edge_to(f)

        s1.init_messages()
        s2.init_messages()
        f.init_messages()

        s2.observed({
            ('a',): 0.7,
            ('b',): 0.3
        })

        s1.send_messages()
        s2.send_messages()

        f.update()
        f.normalize()

        f.send_messages()

        s1.update()
        s1.normalize()

        self.assertClose(s1.belief[('a',)], 0.85)
        self.assertClose(s1.belief[('b',)], 0.15)
        self.assertClose(s2.belief[('a',)], 0.7)
