#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Node representations for factor graph."""

import abc
import operator
from copy import copy

from alex.ml.bn.utils import constant_factor


class NodeError(Exception):
    pass


class IncompatibleNeighborError(NodeError):
    pass


class Node(object):
    """Abstract class for nodes in factor graph."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        self.name = name
        self.incoming_message = {}
        self.belief = None
        self.neighbors = {}

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

    def normalize(self):
        """Normalize belief state."""
        self.belief.normalize()


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


class DiscreteConvertedFactorNode(DiscreteFactorNode):
    """Node containing factor and a function, which preprocess values."""

    def __init__(self, name, factor, function):
        super(DiscreteConvertedFactorNode, self).__init__(name, factor)
        self.function = function

    def update(self):
        product_of_messages = reduce(operator.mul,
                                     self.incoming_message.values())
        self.belief = product_of_messages.multiply_by_converted(self.factor,
                                                                self.function)


class DirichletParameterNode(VariableNode):
    """Node containing parameter."""

    def __init__(self, name, alpha):
        super(DirichletParameterNode, self).__init__(name)
        self.alpha = alpha

    def message_to(self, node):
        node.message_from(self, self.alpha - self.incoming_message[node.name] + 1)

    def message_from(self, node, alpha):
        self.incoming_message[node.name] = alpha

    def update(self):
        pass


class DirichletFactorNode(FactorNode):
    """Node containing dirichlet factor."""

    def __init__(self, name):
        super(DirichletFactorNode, self).__init__(name)
        self.parents = []
        self.child = None
        self.parameters = {}

    def message_to(self, node):
        if isinstance(node, DirichletParameterNode):
            self._compute_message_to_parameter(self)
        elif isinstance(node, DiscreteVariableNode):
            cavity = self.belief / self.incoming_message[node.name]
            sum_of_alphas = self.incoming_parameter.marginalize(self.parents)
            expected_value = self.incoming_parameter / sum_of_alphas
            factor = cavity * expected_value
            msg = factor.marginalize([node.name])
            node.message_from(self, msg)
        else:
            raise IncompatibleNeighborError()

    def message_from(self, node, message):
        if isinstance(node, DirichletParameterNode):
            self._message_from_parameter(node, message)
        else:
            self._message_from_variable(node, message)

    def update(self):
        self.belief = reduce(operator.mul, self.incoming_message.values())

    def add_neighbor(self, node, parent=True, parameter_assignment=None, **kwargs):
        if isinstance(node, DirichletParameterNode):
            self.parameters[node.name] = node
            self.parameters_mapping[parameter_assignment] = node
        else:
            self.neighbors[node.name] = node
            if parent:
                self.parents.append(node)
            else:
                self.child = node

    def _compute_message_to_parameter(self):
        sum_of_alphas = self.incoming_parameter.marginalize([self.child])
        expected_value = self.incoming_parameter / sum_of_alphas

        w0 = self.belief * expected_value