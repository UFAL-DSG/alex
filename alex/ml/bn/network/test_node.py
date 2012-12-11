#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=C0111

import unittest

from bn.factor import DiscreteFactor
from bn.network.node import DiscreteVariableNode

class TestNode(unittest.TestCase):

    def setUp(self):
        self.observation_factor = DiscreteFactor(
            {
                "Command": ["save", "del"],
                "Observation": ["osave", "odel"]
            },
            {
            # P(Command | Observation)
                ("save", "osave"): 0.8,
                ("save", "odel"): 0.2,
                ("del", "osave"): 0.2,
                ("del", "odel"): 0.8,
            })

        self.command_variable_factor = DiscreteFactor(
            {
                "Command": ["save", "del"]
            },
            {
                ("save",): 1,
                ("del",): 1,
            })

        self.observation_variable_factor = DiscreteFactor(
            {
                "Observation": ["osave", "odel"]
            },
            {
                ("osave",): 1,
                ("odel",): 0,
            })


    def test_factors(self):
        m_com_var_to_obs_fac = self.command_variable_factor
        m_obs_var_to_obs_fac = self.observation_variable_factor
        obs_fac_belief = (self.observation_factor * m_obs_var_to_obs_fac *
                          m_com_var_to_obs_fac)
        print obs_fac_belief

        temp = obs_fac_belief / m_com_var_to_obs_fac
        m_obs_fac_to_com_var = temp.marginalize(["Command"])
        print m_obs_fac_to_com_var

        temp = obs_fac_belief / m_obs_var_to_obs_fac
        m_obs_fac_to_obs_var = temp.marginalize(["Observation"])
        print m_obs_fac_to_obs_var
