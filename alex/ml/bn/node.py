#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Node representations for factor graph."""

import abc
import operator
import numpy as np
from copy import copy, deepcopy
from collections import defaultdict

from alex.ml.bn.utils import constant_factor


class NodeError(Exception):
    pass


class IncompatibleNeighborError(NodeError):
    pass


class Node(object):
    """Abstract class for nodes in factor graph."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name, aliases={}):
        self.name = name
        self.incoming_message = {}
        self.belief = None
        self.neighbors = {}
        self.aliases = aliases

    def connect(self, node, **kwargs):
        """Add a neighboring node."""
        self.add_neighbor(node, **kwargs)
        node.add_neighbor(self, **kwargs)

    @abc.abstractmethod
    def message_to(self, node):
        """Compute a message to neighboring node."""
        raise NotImplementedError()

    @abc.abstractmethod
    def message_from(self, node, message):
        """Save message from neighboring node."""
        raise NotImplementedError()

    @abc.abstractmethod
    def update(self):
        """Update belief state."""
        raise NotImplementedError()

    @abc.abstractmethod
    def add_neighbor(self, node):
        raise NotImplementedError()

    def send_messages(self):
        """Send messages to all neighboring nodes."""
        self.update()
        for neighbor in self.neighbors.values():
            self.message_to(neighbor)

    def normalize(self, parents=None):
        """Normalize belief state."""
        self.belief.normalize(parents)

    @abc.abstractmethod
    def init_messages(self):
        raise NotImplementedError()

    def rename_msg(self, msg):
        if self.aliases:
            msg.rename_variables(self.aliases)
        return msg


class FactorNode(Node):
    pass


class VariableNode(Node):
    pass


class DiscreteVariableNode(VariableNode):
    """Node containing variable."""

    def __init__(self, name, values):
        super(DiscreteVariableNode, self).__init__(name)
        self.values = values
        self.belief = constant_factor([name], {name: values}, len(values))
        self.is_observed = False

    def message_to(self, node):
        if self.is_observed:
            node.message_from(self, copy(self.belief))
        else:
            node.message_from(self, self.belief / self.incoming_message[node.name])

    def message_from(self, node, message):
        if not self.is_observed:
            self.incoming_message[node.name] = message

    def update(self):
        if not self.is_observed:
            self.belief = reduce(operator.mul, self.incoming_message.values())

    def observed(self, assignment_dict):
        """Set observation."""
        if assignment_dict is not None:
            self.is_observed = True
            self.belief.observed(assignment_dict)
        else:
            self.is_observed = False
            self.belief.observed(None)

    def add_neighbor(self, node, **kwargs):
        self.neighbors[node.name] = node
        self.incoming_message[node.name] = constant_factor(
            [self.name],
            {self.name: self.values},
            len(self.values))

    def most_probable(self, n=None):
        self.normalize()
        return self.belief.most_probable(n)

    def init_messages(self):
        for (name, node) in self.neighbors.iteritems():
            self.incoming_message[name] = constant_factor(
                [self.name],
                {self.name: self.values},
                len(self.values))


class DiscreteFactorNode(FactorNode):
    """Node containing factor."""

    def __init__(self, name, factor):
        super(DiscreteFactorNode, self).__init__(name)
        self.factor = factor
        self.parameters = {}

    def message_to(self, node):
        belief_without_node = self.belief / self.incoming_message[node.name]
        message = belief_without_node.marginalize([node.name])
        node.message_from(self, message)

    def message_from(self, node, message):
        self.incoming_message[node.name] = message

    def update(self):
        self.belief = self.factor * reduce(operator.mul,
                                           self.incoming_message.values())

    def add_neighbor(self, node, **kwargs):
        self.neighbors[node.name] = node
        self.incoming_message[node.name] = constant_factor(
            [node.name],
            {node.name: node.values},
            len(node.values))

    def init_messages(self):
        for (name, node) in self.neighbors.iteritems():
            self.incoming_message[name] = constant_factor(
                [name],
                {name: node.values},
                len(node.values))


class DirichletParameterNode(VariableNode):
    """Node containing parameter."""

    def __init__(self, name, alpha, aliases={}):
        super(DirichletParameterNode, self).__init__(name, aliases)
        self.alpha = alpha
        self.outgoing_message = {}
        self.aliases = {}

    def message_to(self, node):
        self.outgoing_message[node.name] = self.alpha + 1 - self.incoming_message[node.name]
        node.message_from(self, self.outgoing_message[node.name])

    def message_from(self, node, message):
        message = self.rename_msg(message)
        self.alpha = self.alpha + message - self.incoming_message[node.name]
        self.incoming_message[node.name] = message

    def add_neighbor(self, node):
        self.neighbors[node.name] = node
        self.incoming_message[node.name] = constant_factor(self.alpha.variables,
                                                           self.alpha.variable_values,
                                                           self.alpha.factor_length)
        self.outgoing_message[node.name] = self.alpha - self.incoming_message[node.name] + 1

    def update(self):
        pass

    def normalize(self, parents=None):
        pass

    def init_messages(self):
        for (name, node) in self.neighbors.iteritems():
            self.incoming_message[name] = constant_factor(self.alpha.variables,
                                                          self.alpha.variable_values,
                                                          self.alpha.factor_length)

            self.outgoing_message[name] = self.alpha + 1 - self.incoming_message[node.name]

    def _rename_vars_in_message(self, node, message):
        return message


class DirichletFactorNode(FactorNode):
    """Node containing dirichlet factor."""

    def __init__(self, name, aliases={}):
        super(DirichletFactorNode, self).__init__(name, aliases)
        self.parents = []
        self.child = None
        self.parameters = {}
        self.incoming_parameter = None
        self.incoming_message = {}

    def message_to(self, node):
        if isinstance(node, DirichletParameterNode):
            self._compute_message_to_parameter(node)
        elif isinstance(node, DiscreteVariableNode):
            self._compute_message_to_variable(node)
        else:
            raise IncompatibleNeighborError()

    def message_from(self, node, message):
        if isinstance(node, DirichletParameterNode):
            self.incoming_parameter = self.rename_msg(message)
        else:
            self.incoming_message[node.name] = message

    def update(self):
        self.belief = reduce(operator.mul, self.incoming_message.values())

    def add_neighbor(self, node, parent=True, **kwargs):
        self.neighbors[node.name] = node
        if isinstance(node, DirichletParameterNode):
            self.parameters[node.name] = node

            self.incoming_parameter = self.rename_msg(deepcopy(node.alpha))
        else:
            self.neighbors[node.name] = node
            if parent:
                self.parents.append(node.name)
            else:
                self.child = node

            self.incoming_message[node.name] = node.belief
            self.incoming_message[node.name].normalize()

    def normalize(self, parents=None):
        pass

    def init_messages(self):
        for (name, node) in self.neighbors.iteritems():
            if isinstance(node, DirichletParameterNode):
                self.incoming_parameter = node.alpha
            else:
                self.incoming_message[name] = node.belief
                self.incoming_message[name].normalize()

    def _compute_message_to_parameter(self, node):
        alpha = self._approximate_true_marginal()
        message = alpha + 1 - self.incoming_parameter
        node.message_from(self, message)

    def _compute_message_to_variable(self, node):
        cavity = self.belief / self.incoming_message[node.name]
        sum_of_alphas = self.incoming_parameter.marginalize(self.parents)
        expected_value = self.incoming_parameter / sum_of_alphas
        message = cavity * expected_value
        marginalized = message.marginalize([node.name])
        node.message_from(self, marginalized)

    def _approximate_true_marginal(self):
        # Compute w_0*:
        # (1) Compute a product of cavity distributions for variables.
        prod_cavity = reduce(operator.mul, self.incoming_message.itervalues())
        # (2) Compute expected value of theta
        sum_of_alphas = self.incoming_parameter.marginalize(self.parents)
        expected_theta = self.incoming_parameter / sum_of_alphas
        # (3) Multiply (1) and (2).
        msgs = prod_cavity * expected_theta
        # (4) Marginalize child node.
        msgs = msgs.marginalize(self.parents)
        # (5) For j-th assignment, sum every other assignment from (4).
        w_0 = msgs.sum_other()

        # Compute w_k*:
        # (1) w_k* is a product of w_k and expected x_k
        w_k = prod_cavity * expected_theta

        # Normalize weights:
        sum_of_weights = w_0 + w_k.marginalize(self.parents)
        w_0 /= sum_of_weights
        w_k /= sum_of_weights

        # Compute expected value of every part of the mixture:
        # (1) Expected value of theta without any observations.
        expected_values = [w_0 * expected_theta]
        # (2) For each possible value k of a child node, compute expected value
        # of alpha with one observation of k.
        # (2.1) Compute sum of alpha with plus 1.
        sum_of_alphas_1 = self.incoming_parameter.marginalize(self.parents)
        sum_of_alphas_1.add(1)
        # (2.2) Find index of a child variable, so we can check its
        # assignment
        index_of_child = self.incoming_parameter.variables.index(self.child.name)

        for k in self.child.values:
            # (2.3) Create new alphas.
            alpha_k = deepcopy(self.incoming_parameter)
            # (2.4) Add one to every assignment where child variable is
            # assigned to k.
            for i, item in enumerate(alpha_k):
                assignment, value = item
                if assignment[index_of_child] == k:
                    alpha_k.add(1, assignment)

            # (2.5) Compute expected value.
            expected_value_k = alpha_k / sum_of_alphas_1
            # (2.6) Multiply expected value by weight and save.
            w_k_c = w_k.marginalize(self.parents)
            for assignment, value in w_k:
                if assignment[index_of_child] == k:
                    child_assignment = assignment[:index_of_child] + assignment[index_of_child+1:]
                    w_k_c[child_assignment] = value

            expected_value_k_weighted = w_k_c * expected_value_k
            expected_values.append(expected_value_k_weighted)

        # The resulting expected parameters are a sum of weighted expectations
        E_alpha = reduce(operator.add, expected_values)

        # Compute expected value of theta squared:
        alpha = self.incoming_parameter
        expected_alpha_squared = (alpha * (alpha + 1)) / (sum_of_alphas * sum_of_alphas_1)
        # (1) Expected value of theta squared without any observations.
        expected_values_squared = [w_0 * expected_alpha_squared]
        # (2) For each possible value k of a child node, compute expected value
        # of alpha squared with one observation of k.
        # (2.1) Compute sum of alpha plus 2.
        sum_of_alphas_2 = sum_of_alphas_1 + 1
        for k in self.child.values:
            # (2.2) Create new alphas.
            alpha_k = deepcopy(self.incoming_parameter)
            for i, item in enumerate(alpha_k):
                assignment, value = item
                if assignment[index_of_child] == k:
                    alpha_k.add(1, assignment)
            # (2.5) Compute expected value.
            expected_value_k_squared = alpha_k * (alpha_k + 1) / (sum_of_alphas_1 * sum_of_alphas_2)
            # (2.6) Multiply expected value by weight and save.
            w_k_c = w_k.marginalize(self.parents)
            for assignment, value in w_k:
                if assignment[index_of_child] == k:
                    child_assignment = assignment[:index_of_child] + assignment[index_of_child+1:]
                    w_k_c[child_assignment] = value

            expected_value_k_squared_weighted = w_k_c * expected_value_k_squared
            expected_values_squared.append(expected_value_k_squared_weighted)

        # The resulting expected parameters are a sum of weighted expectations
        E_alpha2 = reduce(operator.add, expected_values_squared)

        alpha_0 = defaultdict(list)

        for i, (assignment, value) in enumerate(E_alpha):
            if value > 0:
                parent_assignment = assignment[:index_of_child] + assignment[index_of_child+1:]
                alpha_0[parent_assignment].append((E_alpha[assignment] - E_alpha2[assignment]) /
                                                  (E_alpha2[assignment] - E_alpha[assignment]**2))

        new_alpha_0 = deepcopy(alpha).marginalize(self.parents)
        for assignment, _ in new_alpha_0:
            new_alpha_0[assignment] = np.median([x for x in alpha_0[assignment] if x > 0])

        new_alpha = E_alpha * new_alpha_0
        return new_alpha