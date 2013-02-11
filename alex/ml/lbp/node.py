#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import itertools

from copy import deepcopy
from collections import defaultdict, OrderedDict

import alex.ml.logarithmetic as la
from alex.utils.cache import lru_cache


class GenericNode(object):
    """ This is a base class for all nodes in the Bayesian Network.
    """
    def __init__(self, name, desc):
        self.name = name
        self.desc = desc


class Factor(GenericNode):
    """ This is a base class for all factor nodes in the Bayesian Network.
    """
    def __init__(self, name, desc):
        GenericNode.__init__(self, name, desc)

        # stores a list of connected variables
        self.variables = []
        # stores input messages from variables
        self.input_messages = {}

    def attach_variable(self, variable):
        self.variables.append(variable)

    def detach_variable(self, variable):
        # FIXME: it can be faster if a dictionary would be used for self.variables
        del self.variables[self.variables.index(lambda v:
                                                v.name == variable.name)]

    def get_variables(self):
        return self.variables


class DiscreteFactor(Factor):
    """ This is a base class for discrete factor nodes in the Bayesian Network.

    It can works with full conditional table defined by the provided prob_table
    function.

    The variables must be attached in the same order as are the parameters in the
    prob_table function.
    """
    def __init__(self, name, desc, prob_table):
        Factor.__init__(self, name, desc)

        self.prob_table = prob_table

    def get_output_message(self, variable):
        """ Returns output messages from this factor to the given variable node.

        """

        om = defaultdict(list)

        # FIXME: make this faster by using a dictionary
        variable_index = [v.name for v in self.variables].index(variable.name)
        selected_variables = [(i, v) for i, v in enumerate(
            self.variables) if v.name != variable.name]

        list_of_lists_of_values = [v.get_values() for v in self.variables]

        for x in itertools.product(*list_of_lists_of_values):
            log_prob = self.prob_table(*x)

            for i, v in selected_variables:
                log_prob += self.input_messages[v.name][v.value_2_index[x[i]]]

            om[x[variable_index]].append(log_prob)

        omlp = np.zeros_like(variable.log_probs)
        for v in om:
            omlp[variable.value_2_index[v]] = la.sum(om[v])

        return omlp

    def update_input_messages(self):
        """ Updates all input messages from connected variable nodes.
        """
        # get input messages
        for v in self.variables:
            self.input_messages[v.name] = v.get_output_message(self)


class VariableNode(GenericNode):
    """ This is a base class for all variable nodes in the Bayesian Network.
    """
    def __init__(self, name, desc):
        GenericNode.__init__(self, name, desc)

        # stores a list of connected factors
        # FIXME: you can use an ordered dict to make it faster
        self.forward_factors = []
        self.backward_factors = []
        # stores input messages from factors
        self.input_messages = {}

    def attach_factor(self, factor, forward=False):
        if forward:
            self.forward_factors.append(factor)
        else:
            self.backward_factors.append(factor)

    def detach_factor(self, factor):
        # FIXME: you can use an ordered dict to make it faster
        del self.forward_factors[self.forward_factors.index(
            lambda f: f.name == factor.name)]
        del self.backward_factors[self.backward_factors.index(
            lambda f: f.name == factor.name)]

    def get_factors(self):
        return self.forward_factors + self.backward_factors


class DiscreteNode(VariableNode):
    """This is a class for all nodes with discrete/enumerable values.

    The probabilities are stored in log format.
    """

    def __init__(self, name, desc, card, observed=False):
        VariableNode.__init__(self, name, desc)

        # number of max values in a table
        self.cardinality = card

        # if observed == True then do not update in self.log_probs
        # since they should not change
        self.observed = observed

        # stores indexes of values with respect to the position of its log probabilities in the log_prob array
        self.value_2_index = {}
        self.index_2_value = {}
        # stores log probabilities for val
        self.log_probs = np.array([])

    def __getitem__(self, value):
        return self.log_probs[self.value_2_index[value]]

    def __setitem__(self, value, log_prob):
        try:
            self.log_probs[self.value_2_index[value]] = log_prob
        except KeyError:
            # store a link into the array
            self.value_2_index[value] = len(self.value_2_index)
            self.log_probs = np.append(self.log_probs, [log_prob, ])

            # store a reversed link
            self.index_2_value[self.value_2_index[value]] = value

    def __len__(self):
        return len(self.value_2_index)

    def __str__(self):
        self.explain()

    def get_values(self):
        return self.value_2_index.keys()

    def copy_node(self, node):
        self.value_2_index = deepcopy(node.value_2_index)
        self.index_2_value = deepcopy(node.index_2_value)
        self.log_probs = np.zeros_like(node.log_probs)

#  FIXME: can be removed
#  def set_input_message(self, factor, message):
#    """ Set input message from the given factor.
#    """
#
#    self.input_messages[factor.name] = message

    def get_output_message(self, factor):
        """ Returns output messages from this node to the given factor.

        This is done by subtracting the input log message from the given factor node
        from the current estimate log probabilities in this node.
        """

        try:
            return self.log_probs - self.input_messages[factor.name]
        except KeyError:
            # the factor have not sent any message yet then send the complete marginal probability
            return self.log_probs

    def update_forward_messages(self):
        for factor in self.forward_factors:
            factor.update_input_messages()
            self.input_messages[factor.name] = factor.get_output_message(self)

    def update_backward_messages(self):
        for factor in self.backward_factors:
            factor.update_input_messages()
            self.input_messages[factor.name] = factor.get_output_message(self)

    def update_marginals(self):
        """ Update the marginal probabilities in the node by collecting all input messages and summing them in the log domain.

        Finally, probabilities are normalised to sum to 1.0.
        """

        if not self.observed:
            # update only if this is not an observed node
            self.log_probs = np.zeros_like(self.log_probs)
            for k, im in self.input_messages.iteritems():
                self.log_probs += im

            self.normalise()

    def normalise(self):
        """This function normalise the sum of all probabilities to 1.0"""

        self.log_probs -= la.sum(self.log_probs)

    def get_most_probable_value(self):
        """The function returns the most probable value and its probability
        in a tuple.
        """

        i = np.argmax(self.log_probs)

        return (self.index_2_value[i], self.log_probs[i])

    def get_two_most_probable_values(self):
        """This function returns two most probable values and their probabilities.

        The function returns a tuple consisting of two tuples (value, probability).
        """

        pMax1 = -1.0
        vMax1 = None
        pMax2 = -1.0
        vMax2 = None

        for i in range(len(self.value_2_index)):
            v = self.index_2_value[i]
            p = self.log_probs[i]

            if p > pMax1:
                pMax2, pMax1 = pMax1, p
                vMax2, vMax1 = vMax1, v
            elif p > pMax2:
                pMax2 = p
                vMax2 = v

        return ((vMax1, pMax1), (vMax2, pMax2))

    def explain(self, full=False, linear_prob=False):
        """This function prints the values and their probabilities for this node.
        """

        if full:
            for value in sorted(self.value_2_index.keys()):
                p = self.log_probs[self.value_2_index[value]]
                if linear_prob:
                    p = np.exp(p)
                print("Name: %-20s desc:%-10s Value: %-15s Probability: % .17f"
                      % (self.name, self.desc, value, p))
        else:
            for v in self.get_two_most_probable_values():
                if linear_prob:
                    p = np.exp(v[1])
                print("Name: %-20s desc:%-10s Value: %-15s Probability: % .17f"
                      % (self.name, self.desc, v[0], v[1]))

        p = la.sum(self.log_probs)
        if linear_prob:
            p = np.exp(p)
        print(('Cardinality: %.4d' + ' ' * 54 + ' Total: % .17f')
              % (self.cardinality, p))

        print

if __name__ == '__main__':

    trans_table = {
        'save': {
        'save': 0.9,
        'del': 0.1
        },
        'del': {
        'save': 0.0,
        'del': 1.0
        }
    }

    obs_table = {
        'save': {
        'osave': 0.8,
        'odel': 0.2
        },
        'del': {
        'osave': 0.2,
        'odel': 0.8
        }
    }

    def prob_table(pt_in, *vars):
        pt = pt_in

        for k in vars:
            pt = pt[k]

        try:
            return np.log(pt)
        except:
            return la.zero_prob

    @lru_cache(maxsize=40)
    def prob_table_trans(*vars):
        return prob_table(trans_table, *vars)

    @lru_cache(maxsize=40)
    def prob_table_obs(*vars):
        return prob_table(obs_table, *vars)

    hid1 = DiscreteNode('hid1', '', 2, observed=False)
    hid1['save'] = la.zero_prob
    hid1['del'] = la.zero_prob

    obs1 = DiscreteNode('obs1', '', 2, observed=True)
    obs1['osave'] = la.one_prob
    obs1['odel'] = la.zero_prob

    fact_h1_o1 = DiscreteFactor('fact_h1_o1', '', prob_table_obs)
    fact_h1_o1.attach_variable(hid1)
    fact_h1_o1.attach_variable(obs1)

    hid2 = DiscreteNode('hid2', '', 2, observed=False)
    hid2['save'] = la.zero_prob
    hid2['del'] = la.zero_prob

    fact_h1_h2 = DiscreteFactor('fact_h1_h2', '', prob_table_trans)
    fact_h1_h2.attach_variable(hid1)
    fact_h1_h2.attach_variable(hid2)

    obs2 = DiscreteNode('obs2', '', 2, True)
    obs2['osave'] = la.zero_prob
    obs2['odel'] = la.one_prob

    fact_h2_o2 = DiscreteFactor('fact_h2_o2', '', prob_table_obs)
    fact_h2_o2.attach_variable(hid2)
    fact_h2_o2.attach_variable(obs2)

    obs1.attach_factor(fact_h1_o1)
    hid1.attach_factor(fact_h1_o1, forward=True)
    hid1.attach_factor(fact_h1_h2)
    hid2.attach_factor(fact_h1_h2, forward=True)
    hid2.attach_factor(fact_h2_o2, forward=True)
    obs2.attach_factor(fact_h2_o2)

    nodes_all = [obs1, hid1, hid2, obs2]
    nodes_hid = [hid1, hid2]

    # the update sweeps through the nodes
    for n in nodes_hid:
        n.update_forward_messages()
        n.update_marginals()

    for n in nodes_all:
        n.explain(full=True, linear_prob=True)

    for n in reversed(nodes_hid):
        n.update_backward_messages()
        n.update_marginals()

    print '-' * 120
    for n in nodes_all:
        n.explain(full=True, linear_prob=True)
