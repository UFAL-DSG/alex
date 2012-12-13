#!/usr/bin/env python
# -*- coding: utf8 -*-

# pylint: disable=W0212,C0111,C0103

import unittest

from bn.factor import DiscreteFactor


class TestFactor(unittest.TestCase):

    def setUp(self):
        self.factor1 = DiscreteFactor(
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

        self.f1 = DiscreteFactor(
            {
                'A': [0, 1],
                'B': [0, 1, 2]
            },
            {
                (0, 0): 0.1,
                (0, 1): 0.15,
                (0, 2): 0.2,
                (1, 0): 0.25,
                (1, 1): 0.25,
                (1, 2): 0.05,
            })

        self.f2 = DiscreteFactor(
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

        self.f3 = DiscreteFactor(
            {
                'C': [0, 1],
                'D': ['a', 'b']
            },
            {
                (0, 'a'): 0.1,
                (0, 'b'): 0.1,
                (1, 'a'): 0.1,
                (1, 'b'): 0.1,
            })

    def assertClose(self, first, second, epsilon=0.000001):
        delta = abs(first - second)
        self.assertLess(delta, epsilon)

    def test_strides(self):
        self.assertEquals(self.factor1.strides, {"A": 6, "B": 2, "C": 1})

    def test_get_index_from_assignment(self):
        self.assertEquals(self.factor1._get_index_from_assignment((0, 2, 1)), 5)
        self.assertEquals(self.factor1._get_index_from_assignment((1, 0, 1)), 7)

    def test_get_assignment_from_index(self):
        self.assertEquals(
            self.factor1._get_assignment_from_index(3),
            (0, 1, 1))
        self.assertEquals(
            self.factor1._get_assignment_from_index(10),
            (1, 2, 0))

    def test_marginalize(self):
        factor_a = self.factor1.marginalize(["A"])
        self.assertClose(factor_a[(0,)], 0.2)
        self.assertClose(factor_a[(1,)], 0.8)

        factor_ac = self.factor1.marginalize(["A", "C"])
        self.assertClose(factor_ac[(0, 0)], 0.09)

    def test_multiplication(self):
        f3 = self.f1 * self.f2
        self.assertEqual(f3.variables, ['A', 'B', 'C'])
        self.assertClose(f3[(0, 0, 0)], self.f1[(0, 0)] * self.f2[(0, 0)])
        self.assertClose(f3[(1, 1, 0)], self.f1[(1, 1)] * self.f2[(1, 0)])
        self.assertClose(f3[(1, 2, 1)], self.f1[(1, 2)] * self.f2[(2, 1)])

    def test_division(self):
        f3 = self.factor1 / self.f2
        self.assertClose(f3[(0, 0, 0)], 0.1)
        self.assertClose(f3[(1, 0, 1)], 7 / 15.0)
        self.assertClose(f3[(1, 2, 0)], 0.4)

    def test_mul_div(self):
        f3 = self.factor1 * self.f2
        f4 = f3 / self.f2
        for i in range(f4.factor_length):
            assignment = f4._get_assignment_from_index(i)
            self.assertClose(f4[assignment], self.factor1[assignment])

    def test_string_names(self):
        f4 = self.f2 * self.f3
        self.assertClose(f4[(1, 1, 'a')], 0.025)

