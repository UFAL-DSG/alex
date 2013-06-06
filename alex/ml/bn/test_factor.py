#!/usr/bin/env python
# -*- coding: utf8 -*-

# pylint: disable=W0212,C0111,C0103

import unittest
import numpy as np
import copy

from alex.ml.bn.factor import DiscreteFactor


class TestFactor(unittest.TestCase):

    def assertClose(self, first, second, epsilon=0.000001):
        delta = abs(first - second)
        self.assertLess(delta, epsilon)

    def test_strides(self):
        factor = DiscreteFactor(
            ['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
#               (A, B, C): P(A, B, C)
                (0, 0, 0): 0.01,
                (0, 0, 1): 0.02,
                (0, 1, 0): 0.03,
                (0, 1, 1): 0.04,
                (0, 2, 0): 0.05,
                (0, 2, 1): 0.05,
                (1, 0, 0): 0.06,
                (1, 0, 1): 0.07,
                (1, 1, 0): 0.08,
                (1, 1, 1): 0.09,
                (1, 2, 0): 0.1,
                (1, 2, 1): 0.4,
            })
        self.assertEquals(factor.strides, {"A": 6, "B": 2, "C": 1})

    def test_get_index_from_assignment(self):
        factor = DiscreteFactor(
            ['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
#               (A, B, C): P(A, B, C)
                (0, 0, 0): 0.01,
                (0, 0, 1): 0.02,
                (0, 1, 0): 0.03,
                (0, 1, 1): 0.04,
                (0, 2, 0): 0.05,
                (0, 2, 1): 0.05,
                (1, 0, 0): 0.06,
                (1, 0, 1): 0.07,
                (1, 1, 0): 0.08,
                (1, 1, 1): 0.09,
                (1, 2, 0): 0.1,
                (1, 2, 1): 0.4,
            })
        self.assertEquals(factor._get_index_from_assignment((0, 2, 1)), 5)
        self.assertEquals(factor._get_index_from_assignment((1, 0, 1)), 7)

    def test_get_assignment_from_index(self):
        factor = DiscreteFactor(
            ['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
#               (A, B, C): P(A, B, C)
                (0, 0, 0): 0.01,
                (0, 0, 1): 0.02,
                (0, 1, 0): 0.03,
                (0, 1, 1): 0.04,
                (0, 2, 0): 0.05,
                (0, 2, 1): 0.05,
                (1, 0, 0): 0.06,
                (1, 0, 1): 0.07,
                (1, 1, 0): 0.08,
                (1, 1, 1): 0.09,
                (1, 2, 0): 0.1,
                (1, 2, 1): 0.4,
            })
        self.assertEquals(
            factor._get_assignment_from_index(3),
            (0, 1, 1))
        self.assertEquals(
            factor._get_assignment_from_index(10),
            (1, 2, 0))

    def test_marginalize(self):
        factor = DiscreteFactor(
            ['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
#               (A, B, C): P(A, B, C)
                (0, 0, 0): 0.01,
                (0, 0, 1): 0.02,
                (0, 1, 0): 0.03,
                (0, 1, 1): 0.04,
                (0, 2, 0): 0.05,
                (0, 2, 1): 0.05,
                (1, 0, 0): 0.06,
                (1, 0, 1): 0.07,
                (1, 1, 0): 0.08,
                (1, 1, 1): 0.09,
                (1, 2, 0): 0.1,
                (1, 2, 1): 0.4,
            })
        factor_a = factor.marginalize(["A"])
        self.assertClose(factor_a[(0,)], 0.2)
        self.assertClose(factor_a[(1,)], 0.8)

        factor_ac = factor.marginalize(["A", "C"])
        self.assertClose(factor_ac[(0, 0)], 0.09)

    def test_multiplication(self):
        f1 = DiscreteFactor(
            ['A', 'B'],
            {
                'A': ['a', 'b'],
                'B': [0, 1, 2]
            },
            {
                ('a', 0): 0.1,
                ('a', 1): 0.15,
                ('a', 2): 0.2,
                ('b', 0): 0.25,
                ('b', 1): 0.25,
                ('b', 2): 0.05,
            })

        f2 = DiscreteFactor(
            ['B', 'C'],
            {
                'B': [0, 1, 2],
                'C': [0, 1]
            },
            {
                (0, 0): 0.1,
                (0, 1): 0.15,
                (1, 0): 0.2,
                (1, 1): 0.25,
                (2, 0): 0.25,
                (2, 1): 0.05,
            })
        f3 = f1 * f2
        self.assertEqual(f3.variables, ['A', 'B', 'C'])
        self.assertClose(f3[('a', 0, 0)], f1[('a', 0)] * f2[(0, 0)])
        self.assertClose(f3[('b', 1, 0)], f1[('b', 1)] * f2[(1, 0)])
        self.assertClose(f3[('b', 2, 1)], f1[('b', 2)] * f2[(2, 1)])

    def test_multiplication_different_values(self):
        f1 = DiscreteFactor(
            ['A'],
            {
                'A': ['a1', 'a2']
            },
            {
                ('a1',): 0.8,
                ('a2',): 0.2
            }
        )

        f2 = DiscreteFactor(
            ['B'],
            {
                'B': ['b1', 'b2']
            },
            {
                ('b1',): 0.8,
                ('b2',): 0.2
            }
        )

        f3 = f1 * f2
        self.assertEqual(f3.variables, ['A', 'B'])
        self.assertAlmostEqual(f3[('a1', 'b1')], 0.64)

    def test_fast_mul(self):
        f1 = DiscreteFactor(
            ['A', 'B'],
            {
                'A': ['a', 'b'],
                'B': [0, 1, 2]
            },
            {
                ('a', 0): 0.1,
                ('a', 1): 0.15,
                ('a', 2): 0.2,
                ('b', 0): 0.25,
                ('b', 1): 0.25,
                ('b', 2): 0.05,
            })

        f2 = f1 * f1
        self.assertClose(f2[('a', 2)], 0.04)
        self.assertClose(f2[('b', 1)], 0.0625)

    def test_fast_mul_correct(self):
        f1 = DiscreteFactor(
            ['B'],
            {
                'B': [0, 1, 2]
            },
            {
                (0,): 0.2,
                (1,): 0.25,
                (2,): 0.55,
            })

        f2 = DiscreteFactor(
            ['B'],
            {
                'B': [0, 1]
            },
            {
                (0,): 0.7,
                (1,): 0.3,
            })

        self.assertRaises(ValueError, lambda: f2 * f1)

    def test_division(self):
        factor = DiscreteFactor(
            ['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
#               (A, B, C): P(A, B, C)
                (0, 0, 0): 0.01,
                (0, 0, 1): 0.02,
                (0, 1, 0): 0.03,
                (0, 1, 1): 0.04,
                (0, 2, 0): 0.05,
                (0, 2, 1): 0.05,
                (1, 0, 0): 0.06,
                (1, 0, 1): 0.07,
                (1, 1, 0): 0.08,
                (1, 1, 1): 0.09,
                (1, 2, 0): 0.1,
                (1, 2, 1): 0.4,
            })

        f2 = DiscreteFactor(
            ['B', 'C'],
            {
                'B': [0, 1, 2],
                'C': [0, 1]
            },
            {
                (0, 0): 0.1,
                (0, 1): 0.15,
                (1, 0): 0.2,
                (1, 1): 0.25,
                (2, 0): 0.25,
                (2, 1): 0.05,
            })

        f3 = factor / f2
        self.assertClose(f3[(0, 0, 0)], 0.1)
        self.assertClose(f3[(1, 0, 1)], 7 / 15.0)
        self.assertClose(f3[(1, 2, 0)], 0.4)

    def test_fast_div(self):
        f2 = DiscreteFactor(
            ['B', 'C'],
            {
                'B': [0, 1, 2],
                'C': [0, 1]
            },
            {
                (0, 0): 0.1,
                (0, 1): 0.15,
                (1, 0): 0.2,
                (1, 1): 0.25,
                (2, 0): 0.25,
                (2, 1): 0.05,
            })

        f3 = f2 / f2
        self.assertClose(f3[0, 0], 1)
        self.assertClose(f3[1, 1], 1)

    def test_mul_div(self):
        factor = DiscreteFactor(
            ['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
#               (A, B, C): P(A, B, C)
                (0, 0, 0): 0.01,
                (0, 0, 1): 0.02,
                (0, 1, 0): 0.03,
                (0, 1, 1): 0.04,
                (0, 2, 0): 0.05,
                (0, 2, 1): 0.05,
                (1, 0, 0): 0.06,
                (1, 0, 1): 0.07,
                (1, 1, 0): 0.08,
                (1, 1, 1): 0.09,
                (1, 2, 0): 0.1,
                (1, 2, 1): 0.4,
            })

        f2 = DiscreteFactor(
            ['B', 'C'],
            {
                'B': [0, 1, 2],
                'C': [0, 1]
            },
            {
                (0, 0): 0.1,
                (0, 1): 0.15,
                (1, 0): 0.2,
                (1, 1): 0.25,
                (2, 0): 0.25,
                (2, 1): 0.05,
            })

        f3 = factor * f2
        f4 = f3 / f2
        for i in range(f4.factor_length):
            assignment = f4._get_assignment_from_index(i)
            self.assertClose(f4[assignment], factor[assignment])

    def test_parents_normalize(self):
        f = DiscreteFactor(
            ['A', 'B'],
            {
                'A': ['a1', 'a2'],
                'B': ['b1', 'b2']
            },
            {
                ('a1', 'b1'): 1,
                ('a2', 'b1'): 1,
                ('a1', 'b2'): 1,
                ('a2', 'b2'): 1
            })

        f.normalize(parents=['B'])
        self.assertAlmostEqual(f[('a1', 'b1')], 0.5)

    def test_power(self):
        f = DiscreteFactor(
            ['A', 'B'],
            {
                'A': ['a1', 'a2'],
                'B': ['b1', 'b2']
            },
            {
                ('a1', 'b1'): 0.3,
                ('a1', 'b2'): 0.2,
                ('a2', 'b1'): 0.7,
                ('a2', 'b2'): 0.8,
            })

        f1 = f ** 2
        self.assertAlmostEqual(f[('a1', 'b1')], 0.3)
        self.assertAlmostEqual(f1[('a1', 'b1')], 0.09)

        f2 = f ** np.array([2, 2, 3, 2])
        self.assertAlmostEqual(f2[('a1', 'b1')], 0.09)
        self.assertAlmostEqual(f2[('a2', 'b1')], 0.343)

    def test_alphas(self):
        alpha = DiscreteFactor(
            ['X0', 'X1', 'X2', 'X3'],
            {
                'X0': ['x0_0', 'x0_1'],
                'X1': ['x1_0', 'x1_1'],
                'X2': ['x2_0', 'x2_1'],
                'X3': ['x3_0', 'x3_1'],
            },
            {
                ('x0_0', 'x1_0', 'x2_0', 'x3_0'): 1,
                ('x0_0', 'x1_0', 'x2_0', 'x3_1'): 1,
                ('x0_0', 'x1_0', 'x2_1', 'x3_0'): 1,
                ('x0_0', 'x1_0', 'x2_1', 'x3_1'): 2,
                ('x0_0', 'x1_1', 'x2_0', 'x3_0'): 5,
                ('x0_0', 'x1_1', 'x2_0', 'x3_1'): 1,
                ('x0_0', 'x1_1', 'x2_1', 'x3_0'): 3,
                ('x0_0', 'x1_1', 'x2_1', 'x3_1'): 1,
                ('x0_1', 'x1_0', 'x2_0', 'x3_0'): 1,
                ('x0_1', 'x1_0', 'x2_0', 'x3_1'): 1,
                ('x0_1', 'x1_0', 'x2_1', 'x3_0'): 1,
                ('x0_1', 'x1_0', 'x2_1', 'x3_1'): 1,
                ('x0_1', 'x1_1', 'x2_0', 'x3_0'): 1,
                ('x0_1', 'x1_1', 'x2_0', 'x3_1'): 1,
                ('x0_1', 'x1_1', 'x2_1', 'x3_0'): 1,
                ('x0_1', 'x1_1', 'x2_1', 'x3_1'): 1,
            })

        X0 = DiscreteFactor(
            ['X0'],
            {
                'X0': ['x0_0', 'x0_1']
            },
            {
                ('x0_0',): 1,
                ('x0_1',): 0,
            })

        X1 = DiscreteFactor(
            ['X1'],
            {
                'X1': ['x1_0', 'x1_1']
            },
            {
                ('x1_0',): 0,
                ('x1_1',): 1,
            })

        X2 = DiscreteFactor(
            ['X2'],
            {
                'X2': ['x2_0', 'x2_1']
            },
            {
                ('x2_0',): 1,
                ('x2_1',): 0,
            })

        X3 = DiscreteFactor(
            ['X3'],
            {
                'X3': ['x3_0', 'x3_1']
            },
            {
                ('x3_0',): 1,
                ('x3_1',): 0,
            })

        # Compute message to X1.

        cavity = X0 * X2 * X3
        self.assertAlmostEqual(cavity[('x0_0', 'x2_0', 'x3_0')], 1.0)

        sum_of_alphas = alpha.marginalize(['X1', 'X2', 'X3'])
        self.assertAlmostEqual(sum_of_alphas[('x1_1', 'x2_0', 'x3_0')], 6)

        expected_value = alpha / sum_of_alphas
        self.assertAlmostEqual(expected_value[('x0_0', 'x1_1', 'x2_1', 'x3_0')], 0.75)

        factor = cavity * expected_value
        self.assertAlmostEqual(factor[('x0_0', 'x1_1', 'x2_0', 'x3_0')], 5.0/6)

        msg = factor.marginalize(['X1'])

        # Compute message to X0.

        cavity = X1 * X2 * X3
        self.assertAlmostEqual(cavity[('x1_1', 'x2_0', 'x3_0')], 1.0)
        self.assertAlmostEqual(cavity[('x1_0', 'x2_0', 'x3_0')], 0.0)

        sum_of_alphas = alpha.marginalize(['X1', 'X2', 'X3'])

        expected_value = alpha / sum_of_alphas
        self.assertAlmostEqual(expected_value[('x0_0', 'x1_1', 'x2_0', 'x3_1')], 0.5)

        factor = cavity * expected_value

        msg = factor.marginalize(['X0'])
        self.assertAlmostEqual(msg[('x0_0',)], 5.0/6)

        # Compute w_0.

        sum_of_alphas = alpha.marginalize(['X1', 'X2', 'X3'])
        expected_value = alpha / sum_of_alphas
        belief = X0 * X1 * X2 * X3
        factor = belief * expected_value
        msg = factor.marginalize(['X0'])
        w0 = msg.subtract_superset(factor)

        # Compute w_k.

        # When we want to compute w_k for each j, we can just compute the belief.
        # Each j is denoted by an assignment of parents, which in this case is
        # the assignment of X1, X2, X3, and each k is a value of a child, in
        # this case it's the value of X0.
        # For given j and k, we can get the value of w_jk, by getting one row
        # from w_k.
        w_k = X0 * X1 * X2 * X3

        # Compute expected value of p(\theta)
        sum_of_alphas = alpha.marginalize(['X1', 'X2', 'X3'])
        expected_value_0 = alpha / sum_of_alphas

        sum_of_alphas_plus_1 = alpha.marginalize(['X1', 'X2', 'X3'])
        sum_of_alphas_plus_1.add(1)

        expected_values = [w0 * expected_value_0]

        for k in X0.variable_values['X0']:
            new_alpha = copy.deepcopy(alpha)
            for i, (assignment, value) in enumerate(new_alpha):
                if assignment[0] == k:
                    new_alpha.add(1, assignment)
            expected_value_k = new_alpha / sum_of_alphas_plus_1
            expected_values.append(w_k * expected_value * expected_value_k)



        print w0