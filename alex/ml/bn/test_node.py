#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=C0111

import unittest

from alex.ml.bn.factor import DiscreteFactor
from alex.ml.bn.node import DiscreteVariableNode, DiscreteFactorNode, DirichletFactorNode, DirichletParameterNode


def same_or_different(assignment):
    return all(assignment[0] == x for x in assignment),


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
        obs.connect(fact_h1_o1)
        fact_h1_o1.connect(hid)

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

        s1.connect(f)
        s2.connect(f)

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

    def test_parameter_simple(self):
        alpha = DirichletParameterNode('theta', DiscreteFactor(
            ['X0', 'X1'],
            {
                'X0': ['x0_0', 'x0_1'],
                'X1': ['x1_0'],
            },
            {
                ('x0_0', 'x1_0'): 3,
                ('x0_1', 'x1_0'): 1,
            }
        ))

        factor = DirichletFactorNode('factor')
        x0 = DiscreteVariableNode('X0', ['x0_0', 'x0_1'])
        x1 = DiscreteVariableNode('X1', ['x1_0'])

        x1.observed({('x1_0',): 1})

        factor.connect(alpha)
        factor.connect(x0, parent=False)
        factor.connect(x1, parent=True)

        x0.message_to(factor)
        x1.message_to(factor)

        factor.update()
        self.assertAlmostEqual(factor.belief[('x0_0', 'x1_0')], 0.5)

        factor.message_to(x0)
        factor.message_to(x1)

        x0.update()
        self.assertAlmostEqual(x0.belief[('x0_0',)], 3.0/4)

        factor.message_to(alpha)
        print alpha.alpha

    def test_parameter(self):
        alpha = DirichletParameterNode('theta', DiscreteFactor(
            ['X0', 'X1'],
            {
                'X0': ['x0_0', 'x0_1'],
                'X1': ['x1_0', 'x1_1', 'x1_2'],
            },
            {
                ('x0_0', 'x1_0'): 1,
                ('x0_0', 'x1_1'): 8,
                ('x0_0', 'x1_2'): 1,
                ('x0_1', 'x1_0'): 1,
                ('x0_1', 'x1_1'): 2,
                ('x0_1', 'x1_2'): 1,
            }
        ))

        factor = DirichletFactorNode('factor')
        x0 = DiscreteVariableNode('X0', ['x0_0', 'x0_1'])
        x1 = DiscreteVariableNode('X1', ['x1_0', 'x1_1', 'x1_2'])

        x0.observed({('x0_0',): 1})
        x1.observed({('x1_0',): 0.7, ('x1_1',): 0.2, ('x1_2',): 0.1})

        factor.connect(alpha)
        factor.connect(x0, parent=False)
        factor.connect(x1, parent=True)

        x0.message_to(factor)
        x1.message_to(factor)

        factor.update()

        factor.message_to(x0)
        factor.message_to(x1)

        x0.update()

        factor.message_to(alpha)
        print alpha.alpha

        alpha.message_to(factor)

        factor.update()
        factor.message_to(alpha)
        print alpha.alpha
        raise

