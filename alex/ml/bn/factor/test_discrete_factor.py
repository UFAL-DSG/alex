#!/usr/bin/env python
# -*- coding: utf8 -*-

# pylint: disable=W0212,C0111,C0103

import unittest

from .discrete_factor import DiscreteFactor


class TestFactor(unittest.TestCase):

    def setUp(self):
        self.factor1 = DiscreteFactor(
            ["A", "B", "C"],
            {
                "A": 2,
                "B": 3,
                "C": 2,
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


    def assertClose(self, first, second, epsilon=0.000001):
        delta = abs(first - second)
        self.assertTrue(delta < epsilon)

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
        f1 = DiscreteFactor(
            ['A', 'B'],
            {'A': 2, 'B': 3},
            {
                (0, 0): 0.1,
                (0, 1): 0.15,
                (0, 2): 0.2,
                (1, 0): 0.25,
                (1, 1): 0.25,
                (1, 2): 0.05,
            })
        f2 = DiscreteFactor(
            ['B', 'C'],
            {'B': 3, 'C': 2},
            {
                (0, 0): 0.1,
                (0, 1): 0.15,
                (1, 0): 0.2,
                (1, 1): 0.25,
                (2, 0): 0.25,
                (2, 1): 0.05,
            })
        f3 = f1 * f2
        self.assertEqual(f3.variables, ['A', 'C', 'B'])
        self.assertClose(f3[(0, 0, 0)], f1[(0, 0)] * f2[(0, 0)])
        self.assertClose(f3[(1, 0, 1)], f1[(1, 1)] * f2[(1, 0)])
        self.assertClose(f3[(1, 1, 2)], f1[(1, 2)] * f2[(2, 1)])
