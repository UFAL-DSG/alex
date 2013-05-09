#!/usr/bin/env python
# -*- coding: utf8 -*-

# pylint: disable=W0212,C0111,C0103

import unittest

from bn.factor import DiscreteFactor


class TestFactor(unittest.TestCase):

    def assertClose(self, first, second, epsilon=0.000001):
        delta = abs(first - second)
        self.assertLess(delta, epsilon)

    def test_strides(self):
        factor = DiscreteFactor(['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
            #   (A, B, C): P(A, B, C)
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
        factor = DiscreteFactor(['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
            #   (A, B, C): P(A, B, C)
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
        factor = DiscreteFactor(['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
            #   (A, B, C): P(A, B, C)
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
        factor = DiscreteFactor(['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
            #   (A, B, C): P(A, B, C)
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
        f1 = DiscreteFactor(['A', 'B'],
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

        f2 = DiscreteFactor(['B', 'C'],
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

    def test_fast_mul(self):
        f1 = DiscreteFactor(['A', 'B'],
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
        f1 = DiscreteFactor(['B'],
            {
                'B': [0, 1, 2]
            },
            {
                (0,): 0.2,
                (1,): 0.25,
                (2,): 0.55,
            })

        f2 = DiscreteFactor(['B'],
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
            #   (A, B, C): P(A, B, C)
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
        f2 = DiscreteFactor(['B', 'C'],
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
        factor = DiscreteFactor(['A', 'B', 'C'],
            {
                "A": [0, 1],
                "B": [0, 1, 2],
                "C": [0, 1],
            },
            {
            #   (A, B, C): P(A, B, C)
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

        f2 = DiscreteFactor(['B', 'C'],
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

    def test_rename(self):
        f1 = DiscreteFactor(['B', 'C'],
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

        f2 = DiscreteFactor(['B', 'C'],
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


        f2.rename_variables({'B': 'D'})

        f3 = f1 * f2
        self.assertClose(f3[(1, 1, 2)], 0.0125)
        self.assertEquals(f3.variables, ['B', 'C', 'D'])
        self.assertTrue(all(f1.marginalize('B').factor_table ==
                            f2.marginalize('D').factor_table))
